"""冲压工艺管线：落盘与 flush 写库。禁止 commit。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.repositories.stamping.part.process import StampingProcessRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.services.stamping.part.tailor_weld.service import StampingTailorWeldBlankService
from app.services.stamping.part.upload.cost_ratio_preserver import ProcessCostRatioPreserver
from app.services.stamping.part.upload.orchestrator.types import (
    PipelineBundle,
    PreparedBundle,
    ProgressCallback,
    report_progress,
)
from app.services.stamping.part.upload.persist.files import save_file, save_part_images
from app.services.stamping.part.upload.persist.parts import save_parts, save_processes
from app.services.stamping.part.upload.swing_shear_resolver import collect_swing_shear_part_numbers

logger = logging.getLogger("service.stamping_upload")


def run_stamping_upload_pipeline(
    db: Session,
    prepared: PreparedBundle,
    *,
    current_user: UserVO,
    on_progress: ProgressCallback | None = None,
) -> PipelineBundle:
    part_repo = StampingPartRepository()
    process_repo = StampingProcessRepository()
    cost_ratio_preserver = ProcessCostRatioPreserver()
    tailor_weld_service = StampingTailorWeldBlankService()

    file_info = save_file(
        prepared.file_content,
        prepared.filename,
        prepared.location,
        prepared.vehicle_model,
        prepared.version,
    )
    report_progress(on_progress, 55, "正在保存零件简图...")
    saved_images = save_part_images(prepared.parse_result.images_by_part, file_info.upload_subdir)
    report_progress(on_progress, 70, "正在写入零件、工序与拼焊子片到数据库...")
    try:
        existing_processes = process_repo.list_by_scope(
            db,
            location=file_info.safe_location,
            stamping_suppliers=prepared.supplier_names,
            vehicle_model=prepared.vehicle_model,
        )
        cost_ratio_preserver.apply(
            prepared.parse_result.processes,
            existing_processes,
            prepared.parse_result.parts,
        )
        part_map = save_parts(
            db,
            part_repo,
            prepared.parse_result.parts,
            prepared.vehicle_model,
            prepared.version,
            file_info,
            prepared.parse_result.images_by_part,
            prepared.stamping_supplier,
            prepared.filename,
            tailor_parent_numbers=prepared.tailor_parent_numbers,
            swing_shear_part_numbers=collect_swing_shear_part_numbers(
                prepared.parse_result.parts,
                prepared.parse_result.processes,
            ),
            current_user=current_user,
        )
        mapped_ids = list(part_map.values())
        if mapped_ids:
            process_repo.delete_by_part_ids(db, mapped_ids)
            for part_id in mapped_ids:
                tailor_weld_service.repository.delete_by_part_id(db, part_id)
        tailor_assemblies, tailor_blanks, tailor_warnings = (
            tailor_weld_service.save_parsed_for_upload(
                db,
                prepared.tailor_result.assemblies,
                part_map,
                current_user,
            )
        )
        process_count = save_processes(
            db,
            process_repo,
            prepared.parse_result.processes,
            part_map,
            current_user=current_user,
        )
        register_existing(
            db,
            file_category="stamping_process",
            stored_relpath=to_upload_relpath(file_info.file_path),
            original_filename=prepared.filename,
            current_user=current_user,
            location=file_info.safe_location,
            vehicle_model=prepared.vehicle_model,
            process_version=prepared.version,
            stamping_supplier=prepared.stamping_supplier or None,
        )
        db.flush()
    except IntegrityError:
        raise BusinessException("该范围零件号冲突，请重试覆盖上传") from None

    warnings = list(prepared.parse_result.warnings) + list(prepared.tailor_result.warnings)
    warnings.extend(tailor_warnings)
    parse_time_ms = prepared.parse_result.parse_time_ms + prepared.tailor_result.parse_time_ms
    logger.info(
        "上传处理完成: 零件 %d, 工序 %d, 简图 %d, 拼焊 %d/%d, 解析耗时 %.0fms",
        len(part_map),
        process_count,
        saved_images,
        tailor_assemblies,
        tailor_blanks,
        parse_time_ms,
    )
    return PipelineBundle(
        file_info=file_info,
        saved_images=saved_images,
        part_map=part_map,
        process_count=process_count,
        tailor_assemblies=tailor_assemblies,
        tailor_blanks=tailor_blanks,
        warnings=warnings,
        parse_time_ms=parse_time_ms,
    )
