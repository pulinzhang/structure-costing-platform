"""
合册工艺按号增行。

改图换号：确认表只出新号；零件信息除零件号、版本、生失效外整行抄旧号，
工序整表相同。增加零件禁止按字母版本停旧号，按确认表新插。
已有号一律跳过（改工艺走投产页，避免 8 月合册改行污染 7 月账）。
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.engineering_change_gates import (
    EFFECT_PROCESS_PART,
    find_letter_predecessor_number,
)
from app.common.period import previous_month
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.parsers.stamping.stamping_parser import parse_stamping_excel
from app.repositories.engineering_change.effect_link_repository import (
    EngineeringChangeEffectLinkInsert,
)
from app.schemas.dto.stamping_upload_dto import PartData, ProcessData
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.upload.gates.process_gates import (
    assert_part_not_shared_on_other_l0,
)
from app.services.stamping.part.engineering_change import (
    EngineeringChangePartAsOfRow,
    EngineeringChangeProcessPartSpec,
)
from app.services.stamping.stamping_service import StampingPartService


def persist_process_parts(
    db: Session,
    *,
    process_sheet: bytes | None,
    expire_new_part_numbers: set[str],
    part_change_order_index: dict[str, int],
    exclude_l0_ids: set[int],
    effective_year: int,
    effective_month: int,
    location: str,
    vehicle_model: str,
    current_user: UserVO,
    sort_no_start: int,
    expiry_year: int | None = None,
    expiry_month: int | None = None,
) -> tuple[list[EngineeringChangeEffectLinkInsert], int]:
    if not process_sheet:
        return [], 0

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(process_sheet)
        tmp_path = tmp.name
    try:
        parsed = parse_stamping_excel(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not parsed.parts:
        return [], 0

    stamping = StampingPartService()
    as_of_rows = stamping.list_parts_as_of_for_engineering_change(
        db,
        location=location,
        vehicle_model=vehicle_model,
        as_of_year=effective_year,
        as_of_month=effective_month,
    )
    audit = audit_create(current_user)
    prev_year, prev_month = previous_month(effective_year, effective_month)
    specs: list[EngineeringChangeProcessPartSpec] = []
    link_meta: list[tuple[int | None, str, int]] = []
    sheet_version = (parsed.version or "").strip()

    for parsed_part in parsed.parts:
        part_number = (parsed_part.part_number or "").strip()
        supplier = (parsed_part.stamping_supplier or parsed.stamping_supplier or "").strip()
        if not part_number:
            continue
        if _has_as_of_part(as_of_rows, part_number, supplier):
            continue

        old_row: EngineeringChangePartAsOfRow | None = None
        if part_number in expire_new_part_numbers:
            old_row = _find_letter_predecessor(as_of_rows, part_number, stamping_supplier=supplier)

        if old_row is not None:
            if exclude_l0_ids:
                assert_part_not_shared_on_other_l0(
                    db,
                    location=location,
                    vehicle_model=vehicle_model,
                    part_number=old_row.part_number,
                    as_of_year=effective_year,
                    as_of_month=effective_month,
                    exclude_l0_id=next(iter(exclude_l0_ids)),
                    exclude_l0_ids=exclude_l0_ids,
                )
            part_data, processes = stamping.clone_revise_for_engineering_change(
                db,
                predecessor_id=old_row.id,
                new_part_number=part_number,
                version=sheet_version,
                effective_year=effective_year,
                effective_month=effective_month,
                expiry_year=expiry_year,
                expiry_month=expiry_month,
                excel_filename="",
                excel_sheet_name=parsed_part.excel_sheet_name,
                excel_row=parsed_part.excel_row,
                excel_part_col=parsed_part.excel_part_col,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            )
        else:
            part_data, processes = _part_from_confirmation_sheet(
                parsed_part=parsed_part,
                all_processes=parsed.processes,
                location=location,
                vehicle_model=vehicle_model,
                version=sheet_version,
                supplier=supplier,
                effective_year=effective_year,
                effective_month=effective_month,
                expiry_year=expiry_year,
                expiry_month=expiry_month,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            )

        specs.append(
            EngineeringChangeProcessPartSpec(
                part_data=part_data,
                processes=processes,
                expire_predecessor_id=old_row.id if old_row is not None else None,
                predecessor_expiry_year=prev_year if old_row is not None else None,
                predecessor_expiry_month=prev_month if old_row is not None else None,
            )
        )
        link_meta.append(
            (
                old_row.id if old_row is not None else None,
                part_number,
                part_change_order_index.get(part_number, 0),
            )
        )

    results = stamping.insert_for_engineering_change(db, specs, current_user)
    links: list[EngineeringChangeEffectLinkInsert] = []
    sort_no = sort_no_start
    for result, (before_id, _, change_order_index) in zip(results, link_meta, strict=True):
        links.append(
            EngineeringChangeEffectLinkInsert(
                change_order_id=change_order_index,
                effect_kind=EFFECT_PROCESS_PART,
                before_id=before_id,
                after_id=result.part_id,
                sort_no=sort_no,
            )
        )
        sort_no += 1
    return links, len(results)


def _part_from_confirmation_sheet(
    *,
    parsed_part: Part,
    all_processes: Sequence[Process],
    location: str,
    vehicle_model: str,
    version: str,
    supplier: str,
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    created_by: str | None,
    updated_by: str | None,
) -> tuple[PartData, list[ProcessData]]:
    """增加零件 / 无旧号：按确认表新插。"""
    part_number = str(parsed_part.part_number or "").strip()
    part_data = PartData(
        location=location,
        vehicle_model=vehicle_model,
        version=version,
        stamping_supplier=supplier,
        part_number=part_number,
        excel_filename="",
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        seq_no=getattr(parsed_part, "seq_no", None),
        part_name=getattr(parsed_part, "part_name", None),
        material=getattr(parsed_part, "material", None),
        thickness=getattr(parsed_part, "thickness", None),
        part_weight=getattr(parsed_part, "part_weight", None),
        sheet_length=getattr(parsed_part, "sheet_length", None),
        sheet_width=getattr(parsed_part, "sheet_width", None),
        parts_per_sheet=getattr(parsed_part, "parts_per_sheet", None) or None,
        sheet_type=getattr(parsed_part, "sheet_type", None),
        is_offal_nested=bool(getattr(parsed_part, "is_offal_nested", False)),
        offal_source=getattr(parsed_part, "offal_source", None),
        is_scrap_byproduct=bool(getattr(parsed_part, "is_scrap_byproduct", False)),
        has_swing_shear=bool(getattr(parsed_part, "has_swing_shear", False)),
        die_type=getattr(parsed_part, "die_type", None),
        process_method=getattr(parsed_part, "process_method", None),
        automation=getattr(parsed_part, "automation", None),
        remark=getattr(parsed_part, "remark", None),
        excel_sheet_name=getattr(parsed_part, "excel_sheet_name", None),
        excel_row=getattr(parsed_part, "excel_row", None),
        excel_part_col=getattr(parsed_part, "excel_part_col", None),
        created_by=created_by,
        updated_by=updated_by,
    )
    processes: list[ProcessData] = []
    order = 0
    for process in all_processes:
        if str(process.part_number or "").strip() != part_number:
            continue
        order += 1
        die_sets = getattr(process, "die_sets", None)
        processes.append(
            ProcessData(
                part_id=0,
                process_seq=str(process.process_seq),
                process_order=order,
                die_sets=int(die_sets) if die_sets is not None else 1,
                process_code=getattr(process, "process_code", None),
                die_number=getattr(process, "die_number", None),
                tonnage=getattr(process, "tonnage", None),
                cost_ratio=process.cost_ratio,
                remark=getattr(process, "remark", None) or None,
                created_by=created_by,
                updated_by=updated_by,
            )
        )
    return part_data, processes


def _has_as_of_part(
    rows: list[EngineeringChangePartAsOfRow],
    part_number: str,
    stamping_supplier: str,
) -> bool:
    supplier = (stamping_supplier or "").strip()
    for row in rows:
        if row.part_number != part_number:
            continue
        if (row.stamping_supplier or "").strip() == supplier:
            return True
    return False


def _find_letter_predecessor(
    rows: list[EngineeringChangePartAsOfRow],
    new_number: str,
    *,
    stamping_supplier: str,
) -> EngineeringChangePartAsOfRow | None:
    supplier = (stamping_supplier or "").strip()
    pool = [row for row in rows if (row.stamping_supplier or "").strip() == supplier]
    pred = find_letter_predecessor_number((row.part_number for row in pool), new_number)
    if pred is None:
        return None
    for row in pool:
        if row.part_number == pred:
            return row
    return None
