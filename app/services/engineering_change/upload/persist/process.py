"""
合册工艺按号增行。

改图换号：确认表只出新号；零件信息除零件号、版本、生失效外整行抄变更前零件，
工序整表相同。表页「序号」不互校，改图继承旧行。旧号只认工程变更单，禁止按茎猜前驱。增加零件不停旧号，按确认表新插。
已有号一律跳过（改工艺走投产页，避免 8 月合册改行污染 7 月账）。
增加零件序号 = 该厂该项目已有 seq_no（含已失效）的 max+1，不信确认表序号列。
"""

from __future__ import annotations

import tempfile
from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.engineering_change_gates import EFFECT_PROCESS_PART
from app.common.period import previous_month
from app.parsers.engineering_change.sheet_extract import SHEET_PROCESS
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.parsers.stamping.stamping_parser import parse_stamping_excel
from app.repositories.engineering_change.effect_link_repository import (
    EngineeringChangeEffectLinkInsert,
)
from app.schemas.dto.stamping_upload_dto import PartData, ProcessData
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.part.engineering_change import (
    EngineeringChangePartAsOfRow,
    EngineeringChangeProcessPartSpec,
)
from app.services.stamping.stamping_service import StampingPartService
from app.services.stamping.upload.persist.files import save_part_sketches


def persist_process_parts(
    db: Session,
    *,
    file_content: bytes,
    revise_old_to_new: dict[str, str],
    part_change_order_index: dict[str, int],
    effective_year: int,
    effective_month: int,
    location: str,
    vehicle_model: str,
    current_user: UserVO,
    sort_no_start: int,
    expiry_year: int | None = None,
    expiry_month: int | None = None,
) -> tuple[list[EngineeringChangeEffectLinkInsert], int, str]:
    if not file_content:
        return [], 0, ""

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name
    try:
        parsed = parse_stamping_excel(tmp_path, sheet_title=SHEET_PROCESS)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not parsed.parts:
        return [], 0, (parsed.version or "").strip()

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
    change_order_indexes: list[int] = []
    sheet_version = (parsed.version or "").strip()
    sketch_urls = save_part_sketches(
        parsed.images_by_part,
        location=location,
        vehicle_model=vehicle_model,
        version=sheet_version,
    )
    new_to_old = {new_number: old_number for old_number, new_number in revise_old_to_new.items()}
    next_add_seq_no = stamping.next_seq_no_in_scope_for_engineering_change(
        db, location=location, vehicle_model=vehicle_model
    )

    for parsed_part in parsed.parts:
        part_number = (parsed_part.part_number or "").strip()
        supplier = (parsed_part.stamping_supplier or parsed.stamping_supplier or "").strip()
        if not part_number:
            continue
        if _find_as_of_part(as_of_rows, part_number, stamping_supplier=supplier) is not None:
            continue

        old_row: EngineeringChangePartAsOfRow | None = None
        old_number = new_to_old.get(part_number)
        if old_number:
            old_row = _find_as_of_part(as_of_rows, old_number, stamping_supplier=supplier)

        if old_row is not None:
            part_data, processes = stamping.clone_revise_for_engineering_change(
                db,
                predecessor_id=old_row.id,
                new_part_number=part_number,
                version=sheet_version,
                effective_year=effective_year,
                effective_month=effective_month,
                expiry_year=expiry_year,
                expiry_month=expiry_month,
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
                seq_no=next_add_seq_no,
                effective_year=effective_year,
                effective_month=effective_month,
                expiry_year=expiry_year,
                expiry_month=expiry_month,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            )
            next_add_seq_no += 1
        file_sketch = sketch_urls.get(part_number)
        if file_sketch:
            part_data.sketch_url = file_sketch

        specs.append(
            EngineeringChangeProcessPartSpec(
                part_data=part_data,
                processes=processes,
                expire_predecessor_id=old_row.id if old_row is not None else None,
                predecessor_expiry_year=prev_year if old_row is not None else None,
                predecessor_expiry_month=prev_month if old_row is not None else None,
            )
        )
        change_order_indexes.append(part_change_order_index.get(part_number, 0))

    results = stamping.insert_for_engineering_change(db, specs, current_user)
    links: list[EngineeringChangeEffectLinkInsert] = []
    sort_no = sort_no_start
    for result, change_order_index in zip(results, change_order_indexes, strict=True):
        links.append(
            EngineeringChangeEffectLinkInsert(
                change_order_id=change_order_index,
                effect_kind=EFFECT_PROCESS_PART,
                before_id=result.predecessor_id,
                after_id=result.part_id,
                sort_no=sort_no,
            )
        )
        sort_no += 1
    return links, len(results), sheet_version


def _part_from_confirmation_sheet(
    *,
    parsed_part: Part,
    all_processes: Sequence[Process],
    location: str,
    vehicle_model: str,
    version: str,
    supplier: str,
    seq_no: int,
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    created_by: str | None,
    updated_by: str | None,
) -> tuple[PartData, list[ProcessData]]:
    """增加零件 / 无旧号：按确认表新插；序号接在已有 max+1，不信 Excel 表头序号。"""
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
        seq_no=seq_no,
        part_name=parsed_part.part_name,
        material=parsed_part.material,
        thickness=parsed_part.thickness,
        part_weight=parsed_part.part_weight,
        sheet_length=parsed_part.sheet_length,
        sheet_width=parsed_part.sheet_width,
        parts_per_sheet=parsed_part.parts_per_sheet or None,
        sheet_type=parsed_part.sheet_type,
        is_offal_nested=bool(parsed_part.is_offal_nested),
        offal_source=parsed_part.offal_source,
        is_scrap_byproduct=bool(parsed_part.is_scrap_byproduct),
        has_swing_shear=bool(parsed_part.has_swing_shear),
        die_type=parsed_part.die_type,
        process_method=parsed_part.process_method,
        automation=parsed_part.automation,
        remark=parsed_part.remark,
        created_by=created_by,
        updated_by=updated_by,
    )
    processes: list[ProcessData] = []
    process_order = 0
    for process in all_processes:
        if str(process.part_number or "").strip() != part_number:
            continue
        process_order += 1
        die_sets = process.die_sets
        processes.append(
            ProcessData(
                part_id=0,
                process_seq=str(process.process_seq),
                process_order=process_order,
                die_sets=int(die_sets) if die_sets is not None else 1,
                process_code=process.process_code,
                die_number=process.die_number,
                tonnage=process.tonnage,
                cost_ratio=process.cost_ratio,
                remark=process.remark or None,
                created_by=created_by,
                updated_by=updated_by,
            )
        )
    return part_data, processes


def _find_as_of_part(
    rows: list[EngineeringChangePartAsOfRow],
    part_number: str,
    *,
    stamping_supplier: str,
) -> EngineeringChangePartAsOfRow | None:
    supplier = (stamping_supplier or "").strip()
    for row in rows:
        if row.part_number != part_number:
            continue
        if (row.stamping_supplier or "").strip() == supplier:
            return row
    return None
