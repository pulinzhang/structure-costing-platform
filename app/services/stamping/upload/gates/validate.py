"""冲压工艺导入校验：文件、表头、工序序号、项目范围。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.common.upload_scope_validation import validate_stamping_process_upload_scope
from app.config import settings
from app.exceptions.base import BusinessException
from app.parsers.stamping.models.process import Process
from app.services.masterdata.supplier import SupplierService
from app.services.masterdata.vehicle_model import VehicleModelService
from app.services.stamping.process_seq_validator import (
    ProcessSeqOccurrence,
    find_duplicate_process_seqs,
    format_duplicate_process_seq_issues,
)


def validate_upload_file(*, filename: str, file_content: bytes) -> None:
    if not filename:
        raise BusinessException("未提供文件名")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {".xlsx", ".xls"}:
        raise BusinessException(f"不支持的文件类型: {ext}，仅支持 .xlsx / .xls")
    if not file_content:
        raise BusinessException("上传文件为空")
    if len(file_content) > settings.MAX_UPLOAD_SIZE:
        raise BusinessException(f"文件过大，最大支持 {settings.MAX_UPLOAD_SIZE // (1024 * 1024)}MB")


def require_parsed_scope_headers(*, parsed_vehicle: str, parsed_supplier: str) -> tuple[str, str]:
    vehicle = (parsed_vehicle or "").strip()
    if not vehicle:
        raise BusinessException("Excel 未解析到项目，无法导入")
    supplier = (parsed_supplier or "").strip()
    if not supplier:
        raise BusinessException("Excel 未解析到冲压承制公司，无法导入")
    return vehicle, supplier


def require_no_duplicate_process_seqs(processes: list[Process]) -> None:
    duplicate_seqs = find_duplicate_process_seqs(
        [
            ProcessSeqOccurrence(
                part_number=process.part_number,
                process_seq=process.process_seq,
                excel_row=process.excel_row,
            )
            for process in processes
        ]
    )
    if duplicate_seqs:
        raise BusinessException(
            format_duplicate_process_seq_issues(duplicate_seqs, source_name="工艺确认表")
        )


def resolve_stamping_upload_scope(
    db: Session,
    *,
    parsed_vehicle: str,
    parsed_supplier: str,
    parsed_version: str | None,
) -> tuple[str, str, str, str, list[str]]:
    clock = now()
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
        version=parsed_version,
    )
    supplier_names = supplier_service.expand_for_query(db, canonical_supplier)
    return (
        scope.location,
        scope.vehicle_model,
        scope.version,
        canonical_supplier,
        supplier_names,
    )
