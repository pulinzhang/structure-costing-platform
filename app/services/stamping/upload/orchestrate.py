"""冲压工艺上传：解析编排（校验范围 → 落盘 → 写库）。"""

from __future__ import annotations

import logging
import os
import tempfile
from collections.abc import Callable

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.timezone import now
from app.common.upload_scope_validation import validate_stamping_process_upload_scope
from app.exceptions.base import BusinessException
from app.parsers.stamping.stamping_parser import parse_stamping_excel
from app.parsers.stamping.tailor_weld_parser import parse_tailor_weld_excel
from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.schemas.dto.stamping_upload_dto import UploadResult
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.services.masterdata.supplier import SupplierService
from app.services.masterdata.vehicle_model import VehicleModelService
from app.services.stamping.process_seq_validator import (
    ProcessSeqOccurrence,
    find_duplicate_process_seqs,
    format_duplicate_process_seq_issues,
)
from app.services.stamping.tailor_weld_blank_service import StampingTailorWeldBlankService
from app.services.stamping.upload.cost_ratio_preserver import ProcessCostRatioPreserver
from app.services.stamping.upload.persist import (
    canonicalize_materials,
    save_file,
    save_part_images,
    save_parts,
    save_processes,
)
from app.services.stamping.upload.swing_shear_resolver import collect_swing_shear_part_numbers

ProgressCallback = Callable[[int, str], None]

logger = logging.getLogger("service.stamping_upload")


def process_upload(
    db: Session,
    *,
    part_repo: StampingPartRepository,
    process_repo: StampingProcessRepository,
    cost_ratio_preserver: ProcessCostRatioPreserver,
    tailor_weld_service: StampingTailorWeldBlankService,
    file_content: bytes,
    filename: str,
    current_user: UserVO,
    progress_callback: ProgressCallback | None = None,
) -> UploadResult:
    """
    处理冲压工艺文件上传（完整业务流程）。

    主数据：解析完成后用库中已设比率回写工序，再删除旧数据并写入；
    删除与写入在同一事务中，全部成功或全部回滚。
    项目与冲压工厂从表头解析；基地由项目主数据带出。
    """
    clock = now()

    def _report(progress: int, msg: str) -> None:
        if progress_callback:
            progress_callback(progress, msg)

    _report(5, "正在读取并解析 Excel...")
    with tempfile.NamedTemporaryFile(delete=False, suffix=filename) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name

    try:
        parse_result = parse_stamping_excel(tmp_path)
        tailor_result = parse_tailor_weld_excel(tmp_path)
        parsed_vehicle = (parse_result.vehicle_model or "").strip()
        if not parsed_vehicle:
            raise BusinessException("Excel 未解析到项目，无法导入")
        parsed_supplier = (parse_result.stamping_supplier or "").strip()
        if not parsed_supplier:
            raise BusinessException("Excel 未解析到冲压承制公司，无法导入")
        location, vehicle_model = VehicleModelService().require_introducible_by_code(
            db,
            parsed_vehicle,
            clock.year,
            clock.month,
        )
        supplier_service = SupplierService()
        canonical_supplier = supplier_service.require_enabled(db, parsed_supplier)
        scope = validate_stamping_process_upload_scope(
            location=location,
            stamping_supplier=canonical_supplier,
            vehicle_model=vehicle_model,
            version=parse_result.version,
        )
        location = scope.location
        vehicle_model = scope.vehicle_model
        version = scope.version
        stamping_supplier = canonical_supplier
        supplier_names = supplier_service.expand_for_query(db, canonical_supplier)
        tailor_parent_numbers = set(tailor_result.parent_part_numbers)

        duplicate_seqs = find_duplicate_process_seqs(
            [
                ProcessSeqOccurrence(
                    part_number=process.part_number,
                    process_seq=process.process_seq,
                    excel_row=process.excel_row,
                )
                for process in parse_result.processes
            ]
        )
        if duplicate_seqs:
            raise BusinessException(
                format_duplicate_process_seq_issues(duplicate_seqs, source_name="工艺确认表")
            )
        canonicalize_materials(db, parse_result.parts, tailor_result.assemblies)

        logger.info(
            "解析 Excel 完成：%d 个零件、%d 道工序、%d 个拼焊总成",
            len(parse_result.parts),
            len(parse_result.processes),
            tailor_result.assembly_count,
        )
        _report(
            40,
            f"解析完成：{len(parse_result.parts)} 个零件、"
            f"{len(parse_result.processes)} 道工序、"
            f"{tailor_result.assembly_count} 个拼焊件，正在保存文件...",
        )

        file_info = save_file(file_content, filename, location, vehicle_model, version)

        _report(55, "正在保存零件简图...")
        saved_images = save_part_images(parse_result.images_by_part, file_info.upload_subdir)

        _report(70, "正在写入零件、工序与拼焊子片到数据库...")
        try:
            existing_processes = process_repo.list_by_scope(
                db,
                location=file_info.safe_location,
                stamping_suppliers=supplier_names,
                vehicle_model=vehicle_model,
                version=version,
            )
            cost_ratio_preserver.apply(
                parse_result.processes,
                existing_processes,
                parse_result.parts,
            )
            part_map = save_parts(
                db,
                part_repo,
                parse_result.parts,
                vehicle_model,
                version,
                file_info,
                parse_result.images_by_part,
                stamping_supplier,
                filename,
                tailor_parent_numbers=tailor_parent_numbers,
                swing_shear_part_numbers=collect_swing_shear_part_numbers(
                    parse_result.parts,
                    parse_result.processes,
                ),
                current_user=current_user,
            )
            tailor_assemblies, tailor_blanks, tailor_warnings = (
                tailor_weld_service.save_parsed_for_upload(
                    db,
                    tailor_result.assemblies,
                    part_map,
                    current_user,
                )
            )
            process_count = save_processes(
                db, process_repo, parse_result.processes, part_map, current_user=current_user
            )

            warnings = list(parse_result.warnings) + list(tailor_result.warnings)
            warnings.extend(tailor_warnings)
            parse_time_ms = parse_result.parse_time_ms + tailor_result.parse_time_ms

            logger.info(
                "上传处理完成: 零件 %d, 工序 %d, 简图 %d, 拼焊 %d/%d, 解析耗时 %.0fms",
                len(part_map),
                process_count,
                saved_images,
                tailor_assemblies,
                tailor_blanks,
                parse_time_ms,
            )
            _report(95, "正在提交事务...")

            register_existing(
                db,
                file_category="stamping_process",
                stored_relpath=to_upload_relpath(file_info.file_path),
                original_filename=filename,
                current_user=current_user,
                location=file_info.safe_location,
                vehicle_model=vehicle_model,
                process_version=version,
                stamping_supplier=stamping_supplier or None,
            )

            result = UploadResult(
                filename=filename,
                new_filename=file_info.new_filename,
                size=len(file_content),
                path=file_info.file_path,
                location=location,
                vehicle_model=vehicle_model,
                version=version,
                parts_count=len(part_map),
                processes_count=process_count,
                images_count=saved_images,
                tailor_weld_assembly_count=tailor_assemblies,
                tailor_weld_blank_count=tailor_blanks,
                warnings=warnings,
                parse_time_ms=parse_time_ms,
            )
            db.commit()
            return result
        except IntegrityError:
            db.rollback()
            raise BusinessException("该范围零件号冲突，请重试覆盖上传") from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("冲压工艺上传落库失败")
            raise
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
