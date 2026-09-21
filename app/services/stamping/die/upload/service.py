"""冲压模具布点上传。"""

from __future__ import annotations

import logging
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.period import SOP_NEW_NUMBER_REJECT
from app.common.timezone import now
from app.common.vehicle_model import normalize_vehicle_model
from app.config import settings
from app.exceptions.base import BusinessException
from app.models.stamping.die import StampingDiePart
from app.parsers.stamping.die.parser import (
    ParsedDiePart,
    layout_has_die_mass,
    parse_die_layout_excel,
)
from app.repositories.persist import apply_payload_fields
from app.repositories.stamping.die.repository import (
    StampingDiePartRepository,
    StampingDieProcessRepository,
)
from app.schemas.dto.stamping_die_dto import StampingDiePartInsert, StampingDieProcessInsert
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    TASK_TYPE_STAMPING_DIE_UPLOAD,
    AsyncTaskService,
)
from app.services.async_task.worker_runner import WorkerTaskOutcome
from app.services.file_trace.path_utils import to_upload_relpath
from app.services.file_trace.register import register_existing
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.services.stamping.die.rules.weight_check import (
    DieWeightCheckRow,
    find_die_weight_mismatches,
    format_die_weight_mismatch_issues,
)
from app.services.stamping.die.upload.alloc_preserver import (
    preserve_die_alloc,
    resolve_part_ratios,
)
from app.services.stamping.die.upload.die_number_assigner import assign_die_numbers
from app.services.stamping.die.upload.template_builder import build_die_layout_template
from app.services.stamping.part.rules.process_seq_validator import (
    ProcessSeqOccurrence,
    find_duplicate_process_seqs,
    format_duplicate_process_seq_issues,
)

ProgressCallback = Callable[[int, str], None]
logger = logging.getLogger("service.stamping_die_upload")


@dataclass(slots=True)
class DieUploadResult:
    parts_count: int
    processes_count: int
    assigned_die_number_count: int
    location: str
    vehicle_model: str


class StampingDieUploadService:
    def __init__(self, db: Session):
        self.db = db
        self.die_part_repo = StampingDiePartRepository()
        self.die_process_repo = StampingDieProcessRepository()

    @staticmethod
    def build_template() -> tuple[bytes, str]:
        return build_die_layout_template()

    def process_upload(
        self,
        *,
        file_content: bytes,
        filename: str,
        location: str,
        vehicle_model: str,
        current_user: UserVO,
        progress_callback: ProgressCallback | None = None,
    ) -> DieUploadResult:
        clock = now()
        location, selected = VehicleModelService().require_introducible(
            self.db,
            (location or "").strip(),
            (vehicle_model or "").strip(),
            clock.year,
            clock.month,
        )
        vehicle_model = selected

        def report(progress: int, message: str) -> None:
            if progress_callback:
                progress_callback(progress, message)

        report(10, "正在解析模具布点文件...")
        suffix = Path(filename).suffix or ".xlsx"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        try:
            parsed = parse_die_layout_excel(tmp_path, filename=filename)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        parsed_vehicle = normalize_vehicle_model(parsed.vehicle_model)
        if not parsed_vehicle:
            raise BusinessException(
                "无法从文件名识别项目，请确认文件名含「项目冲压模具布点工艺清单」"
            )
        VehicleModelService().assert_matches_selected(vehicle_model, parsed_vehicle)
        if not parsed.parts:
            raise BusinessException("未解析到零件数据")
        if not layout_has_die_mass(parsed.parts):
            raise BusinessException(
                "未读到模具长/宽/高或预估重量。当前文件更像工艺确认表（只有工序和吨位），"
                "请上传含「模具长/模具宽/模具高」或「预估重量／模具重量」列的模具布点清单"
            )

        duplicate_seqs = find_duplicate_process_seqs(
            [
                ProcessSeqOccurrence(
                    part_number=part.part_number,
                    process_seq=process.process_seq,
                    excel_row=process.excel_row,
                )
                for part in parsed.parts
                for process in part.processes
            ]
        )
        if duplicate_seqs:
            raise BusinessException(
                format_duplicate_process_seq_issues(duplicate_seqs, source_name="模具布点清单")
            )

        weight_issues = find_die_weight_mismatches(
            [
                DieWeightCheckRow(
                    part_number=part.part_number,
                    process_seq=process.process_seq,
                    excel_row=process.excel_row,
                    die_length=process.die_length,
                    die_width=process.die_width,
                    die_height=process.die_height,
                    hollow_factor=process.hollow_factor,
                    estimated_weight_t=process.estimated_weight_t,
                )
                for part in parsed.parts
                for process in part.processes
            ]
        )
        if weight_issues:
            raise BusinessException(format_die_weight_mismatch_issues(weight_issues))

        existing = self.die_part_repo.list_existing_in_scope(
            self.db, location=location, vehicle_model=vehicle_model
        )
        existing_map = {(part.part_number or "").strip(): part for part in existing}
        file_numbers = [(part.part_number or "").strip() for part in parsed.parts]
        if existing_map:
            unknown = [number for number in file_numbers if number and number not in existing_map]
            if unknown:
                raise BusinessException(SOP_NEW_NUMBER_REJECT)
        for parsed_part in parsed.parts:
            current = existing_map.get((parsed_part.part_number or "").strip())
            if current is None:
                continue
            by_seq = {
                (process.process_seq or "").strip(): (process.die_number or "").strip()
                for process in current.processes
                if (process.process_seq or "").strip() and (process.die_number or "").strip()
            }
            for process in parsed_part.processes:
                if (process.die_number or "").strip():
                    continue
                inherited = by_seq.get((process.process_seq or "").strip())
                if inherited:
                    process.die_number = inherited
        assigned = assign_die_numbers(
            vehicle_model=vehicle_model,
            parts=parsed.parts,
            existing_numbers=self.die_process_repo.list_die_numbers_for_scope(
                self.db, location=location, vehicle_model=vehicle_model
            ),
        )

        report(40, "正在保存文件...")
        stored_path = self._save_file(file_content, filename, location, vehicle_model)
        preserved = preserve_die_alloc(existing)
        effective_year, effective_month, expiry_year, expiry_month = (
            VehicleModelService().project_sop_period(self.db, location, vehicle_model)
        )

        report(55, "正在按号对齐写入...")
        try:
            audit = audit_create(current_user)
            skip_on_update = frozenset(
                {
                    "id",
                    "seq_no",
                    "version",
                    "effective_year",
                    "effective_month",
                    "expiry_year",
                    "expiry_month",
                    "created_by",
                    "created_at",
                }
            )
            created_parts: list[StampingDiePart] = []
            targets: list[tuple[ParsedDiePart, StampingDiePart]] = []
            to_create: list[StampingDiePartInsert] = []
            create_parsed: list[ParsedDiePart] = []
            for parsed_part in parsed.parts:
                payload = StampingDiePartInsert(
                    location=location,
                    vehicle_model=vehicle_model,
                    stamping_supplier=None,
                    version=None,
                    seq_no=parsed_part.seq_no,
                    part_number=parsed_part.part_number,
                    part_name=parsed_part.part_name,
                    material=parsed_part.material,
                    thickness=parsed_part.thickness,
                    part_weight=parsed_part.part_weight,
                    sheet_length=parsed_part.sheet_length,
                    sheet_width=parsed_part.sheet_width,
                    sheet_shape=parsed_part.sheet_shape,
                    parts_per_sheet=parsed_part.parts_per_sheet,
                    material_consumption=parsed_part.material_consumption,
                    material_utilization=parsed_part.material_utilization,
                    estimated_weight_subtotal_t=parsed_part.estimated_weight_subtotal_t,
                    die_type=parsed_part.die_type,
                    die_method=parsed_part.die_method,
                    production_mode=parsed_part.production_mode,
                    needs_end_effector=parsed_part.needs_end_effector,
                    part_grade=parsed_part.part_grade,
                    remark=parsed_part.remark,
                    excel_filename=filename,
                    excel_sheet_name=parsed_part.excel_sheet_name,
                    excel_row=parsed_part.excel_row,
                    excel_part_col=parsed_part.excel_part_col,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                    effective_year=effective_year,
                    effective_month=effective_month,
                    expiry_year=expiry_year,
                    expiry_month=expiry_month,
                )
                current = existing_map.get((parsed_part.part_number or "").strip())
                if current is None:
                    to_create.append(payload)
                    create_parsed.append(parsed_part)
                    continue
                apply_payload_fields(current, payload, skip=skip_on_update)
                targets.append((parsed_part, current))
            if to_create:
                created_parts = self.die_part_repo.bulk_create_parts(self.db, to_create)
                for parsed_part, created in zip(create_parsed, created_parts, strict=True):
                    targets.append((parsed_part, created))
            mapped_ids = [part.id for _parsed, part in targets]
            self.die_part_repo.delete_processes_by_part_ids(self.db, mapped_ids)
            process_rows: list[StampingDieProcessInsert] = []
            for parsed_part, part_row in targets:
                ratios = resolve_part_ratios(parsed_part, preserved)
                for order, (process, ratio) in enumerate(
                    zip(parsed_part.processes, ratios, strict=True), start=1
                ):
                    process_rows.append(
                        StampingDieProcessInsert(
                            die_part_id=part_row.id,
                            process_seq=process.process_seq,
                            process_order=order,
                            process_code=process.process_code,
                            die_sets=process.die_sets,
                            die_number=assigned.by_key.get(
                                (parsed_part.part_number.strip(), process.process_seq.strip())
                            ),
                            die_length=process.die_length,
                            die_width=process.die_width,
                            die_height=process.die_height,
                            hollow_factor=process.hollow_factor,
                            estimated_weight_t=process.estimated_weight_t,
                            tonnage=process.tonnage,
                            alloc_ratio=ratio,
                            created_by=audit["created_by"],
                            updated_by=audit["updated_by"],
                        )
                    )
            self.die_process_repo.bulk_create(self.db, process_rows)
            register_existing(
                self.db,
                file_category="stamping_die",
                stored_relpath=to_upload_relpath(stored_path),
                original_filename=filename,
                current_user=current_user,
                location=location,
                vehicle_model=vehicle_model,
            )
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            logger.exception("模具布点上传唯一键冲突")
            raise BusinessException("该基地项目下零件号冲突，请重试覆盖上传") from None
        except Exception:
            self.db.rollback()
            logger.exception("模具布点上传落库失败")
            raise

        report(100, "解析完成")
        return DieUploadResult(
            parts_count=len(targets),
            processes_count=len(process_rows),
            assigned_die_number_count=assigned.assigned_count,
            location=location,
            vehicle_model=vehicle_model,
        )

    def _save_file(
        self,
        file_content: bytes,
        filename: str,
        location: str,
        vehicle_model: str,
    ) -> Path:
        safe_location = location.replace("/", "_").replace("\\", "_")
        safe_vehicle = vehicle_model.replace("/", "_").replace("\\", "_")
        stamp = now().strftime("%Y%m%d_%H%M%S")
        folder = settings.UPLOAD_DIR / safe_location / safe_vehicle / "die"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{stamp}_{filename}"
        target.write_bytes(file_content)
        return target

    @classmethod
    def start_upload(
        cls,
        *,
        db: Session,
        file_content: bytes,
        filename: str,
        location: str,
        vehicle_model: str,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        clock = now()
        location, vehicle_model = VehicleModelService().require_introducible(
            db,
            (location or "").strip(),
            (vehicle_model or "").strip(),
            clock.year,
            clock.month,
        )
        if not filename:
            raise BusinessException("未提供文件名")
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in {".xlsx", ".xls"}:
            raise BusinessException(f"不支持的文件类型: {ext}，仅支持 .xlsx / .xls")
        if not file_content:
            raise BusinessException("上传文件为空")
        if len(file_content) > settings.MAX_UPLOAD_SIZE:
            raise BusinessException(
                f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB"
            )

        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_STAMPING_DIE_UPLOAD,
            message="已提交解析队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            service = cls(db)
            try:
                result = service.process_upload(
                    file_content=file_content,
                    filename=filename,
                    location=location,
                    vehicle_model=vehicle_model,
                    progress_callback=on_progress,
                    current_user=current_user,
                )
            except (BusinessException, ValueError) as error:
                logger.warning("模具上传业务失败: task_id=%s error=%s", task.task_id, error)
                return WorkerTaskOutcome(
                    status=STATUS_FAILED,
                    progress=0,
                    message=str(error),
                )
            success_message = (
                f"上传成功：{result.parts_count} 个零件，{result.processes_count} 道工序"
            )
            if result.assigned_die_number_count:
                success_message += f"，空号已按规则生成 {result.assigned_die_number_count} 条"
            return WorkerTaskOutcome(
                status=STATUS_COMPLETED,
                message=success_message,
                result=asdict(result),
            )

        async_task_service.submit_session_worker(
            task.task_id,
            start_message="后台开始解析...",
            work=work,
            crash_message=lambda error: f"解析异常: {error}",
        )
        return AsyncTaskAcceptedVO(task_id=task.task_id)
