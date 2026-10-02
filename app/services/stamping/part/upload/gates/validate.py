"""冲压工艺导入校验：文件、表头、工序序号、项目范围。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.common.upload_scope_validation import validate_stamping_process_upload_scope
from app.common.workbook_reject import format_workbook_reject
from app.config import settings
from app.exceptions.base import BusinessException
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.services.masterdata.supplier.service import SupplierService
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.services.stamping.part.rules.part_seq_validator import (
    PartSeqOccurrence,
    format_part_seq_issues,
    inspect_part_seq_nos,
)
from app.services.stamping.part.rules.process_seq_validator import (
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


def require_ordinary_part_fields(
    parts: list[Part],
    *,
    tailor_parent_numbers: set[str],
) -> None:
    """普通件零件名称、材质、料厚不得为空。拼焊总成按子片，不走这一条。"""
    parents = {(number or "").strip() for number in tailor_parent_numbers if (number or "").strip()}
    errors: list[str] = []
    for part in parts:
        part_number = (part.part_number or "").strip()
        if not part_number or part_number in parents:
            continue
        missing = [
            label
            for label, filled in (
                ("零件名称", bool((part.part_name or "").strip())),
                ("材质", bool((part.material or "").strip())),
                ("料厚", part.thickness is not None),
            )
            if not filled
        ]
        if not missing:
            continue
        where = f"第 {part.excel_row} 行" if part.excel_row else "未标行号"
        joined = "、".join(missing)
        errors.append(f"{where}零件 {part_number} 是普通件，{joined}是空的。请填上后再上传。")
    if errors:
        raise BusinessException(format_workbook_reject(errors))


def require_consecutive_part_seq_nos(parts: list[Part]) -> None:
    report = inspect_part_seq_nos(
        [
            PartSeqOccurrence(
                part_number=(part.part_number or "").strip(),
                seq_no=int(part.seq_no) if part.seq_no is not None else 0,
                excel_row=part.excel_row,
            )
            for part in parts
            if (part.part_number or "").strip()
        ]
    )
    message = format_part_seq_issues(report)
    if message:
        raise BusinessException(message)


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
