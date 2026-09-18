"""
合册模具布点按号增行。

为何可缺表：青岛 T28 等项目投产本来就没有布点；摊模具才填「零件汇总」。
无表 / 空表 / 解析失败 → warning 跳过，绝不拒收整份合册（与工艺硬门禁不对称）。
"""

from __future__ import annotations

import logging
import tempfile
from decimal import Decimal
from pathlib import Path

from openpyxl.utils.exceptions import InvalidFileException
from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.engineering_change_gates import (
    EFFECT_DIE_PART,
    find_letter_predecessor_number,
)
from app.common.period import previous_month
from app.exceptions.base import BusinessException
from app.parsers.stamping.die.parser import parse_die_layout_excel
from app.repositories.engineering_change.effect_link_repository import (
    EngineeringChangeEffectLinkInsert,
)
from app.schemas.dto.stamping_die_dto import StampingDiePartInsert
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.upload.gates.process_gates import (
    assert_part_not_shared_on_other_l0,
)
from app.services.stamping.die.alloc_preserver import resolve_part_ratios
from app.services.stamping.die.die_number_assigner import assign_die_numbers
from app.services.stamping.die.die_service import StampingDieService
from app.services.stamping.die.engineering_change import (
    EngineeringChangeDieAsOfRow,
    EngineeringChangeDiePartSpec,
    EngineeringChangeDieProcessSpec,
)

logger = logging.getLogger("service.engineering_change.persist_die")


def persist_die_parts(
    db: Session,
    *,
    die_sheet: bytes | None,
    expire_new_part_numbers: set[str],
    part_change_order_index: dict[str, int],
    exclude_l0_ids: set[int],
    has_revise: bool,
    effective_year: int,
    effective_month: int,
    location: str,
    vehicle_model: str,
    current_user: UserVO,
    sort_no_start: int,
    expiry_year: int | None = None,
    expiry_month: int | None = None,
) -> tuple[list[EngineeringChangeEffectLinkInsert], int, list[str]]:
    """
    布点非硬门禁：无表/空表/解析失败 → 跳过。
    写入经 StampingDieService.insert_for_engineering_change。
    """
    warnings: list[str] = []
    if not die_sheet:
        if has_revise:
            warnings.append("未带模具布点表，接受旧号布点与新总成短暂并存")
        return [], 0, warnings

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(die_sheet)
        tmp_path = tmp.name
    try:
        parsed = parse_die_layout_excel(tmp_path)
    except (BusinessException, ValueError, KeyError, OSError, InvalidFileException) as exc:
        logger.info("布点解析跳过: %s", exc)
        warnings.append("模具布点表未能解析零件行，已跳过")
        return [], 0, warnings
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if not parsed.parts:
        return [], 0, warnings

    die = StampingDieService()
    as_of_rows = die.list_parts_as_of_for_engineering_change(
        db,
        location=location,
        vehicle_model=vehicle_model,
        as_of_year=effective_year,
        as_of_month=effective_month,
    )
    existing_by_number = {row.part_number: row for row in as_of_rows}
    audit = audit_create(current_user)
    prev_year, prev_month = previous_month(effective_year, effective_month)

    to_insert = [
        parsed_part
        for parsed_part in parsed.parts
        if (parsed_part.part_number or "").strip()
        and (parsed_part.part_number or "").strip() not in existing_by_number
    ]
    if not to_insert:
        return [], 0, warnings

    for parsed_part in to_insert:
        part_number = parsed_part.part_number.strip()
        if part_number not in expire_new_part_numbers:
            continue
        predecessor = _find_letter_predecessor(existing_by_number, part_number)
        if predecessor is None:
            continue
        by_seq = die.process_die_numbers_for_engineering_change(db, predecessor.id)
        for process in parsed_part.processes:
            if (process.die_number or "").strip():
                continue
            inherited = by_seq.get((process.process_seq or "").strip())
            if inherited:
                process.die_number = inherited

    existing_numbers = die.list_die_numbers_for_scope(
        db, location=location, vehicle_model=vehicle_model
    )
    assigned = assign_die_numbers(
        vehicle_model=vehicle_model,
        parts=to_insert,
        existing_numbers=existing_numbers,
    )

    specs: list[EngineeringChangeDiePartSpec] = []
    link_meta: list[tuple[int | None, int]] = []
    for parsed_part in to_insert:
        part_number = parsed_part.part_number.strip()
        old_row: EngineeringChangeDieAsOfRow | None = None
        if part_number in expire_new_part_numbers:
            old_row = _find_letter_predecessor(existing_by_number, part_number)

        old_ratios: dict[str, Decimal] = {}
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
            old_ratios = die.process_alloc_ratios_for_engineering_change(db, old_row.id)

        preserved = {part_number: old_ratios} if old_ratios else {}
        ratios = resolve_part_ratios(parsed_part, preserved)
        processes: list[EngineeringChangeDieProcessSpec] = []
        for order, (process, ratio) in enumerate(
            zip(parsed_part.processes, ratios, strict=True), start=1
        ):
            seq = (process.process_seq or "").strip()
            die_number = assigned.by_key.get((part_number, seq))
            if die_number is None:
                die_number = (process.die_number or "").strip() or None
            processes.append(
                EngineeringChangeDieProcessSpec(
                    process_seq=process.process_seq,
                    process_order=order,
                    process_code=process.process_code,
                    die_sets=process.die_sets,
                    die_number=die_number,
                    die_length=process.die_length,
                    die_width=process.die_width,
                    die_height=process.die_height,
                    hollow_factor=process.hollow_factor,
                    estimated_weight_t=process.estimated_weight_t,
                    tonnage=process.tonnage,
                    alloc_ratio=ratio,
                )
            )

        specs.append(
            EngineeringChangeDiePartSpec(
                part=StampingDiePartInsert(
                    location=location,
                    vehicle_model=vehicle_model,
                    stamping_supplier=None,
                    version=None,
                    seq_no=old_row.seq_no if old_row is not None else parsed_part.seq_no,
                    part_number=part_number,
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
                    excel_filename="",
                    excel_sheet_name=parsed_part.excel_sheet_name,
                    excel_row=parsed_part.excel_row,
                    excel_part_col=parsed_part.excel_part_col,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                    effective_year=effective_year,
                    effective_month=effective_month,
                    expiry_year=expiry_year,
                    expiry_month=expiry_month,
                ),
                processes=processes,
                expire_predecessor_id=old_row.id if old_row is not None else None,
                predecessor_expiry_year=prev_year if old_row is not None else None,
                predecessor_expiry_month=prev_month if old_row is not None else None,
            )
        )
        link_meta.append(
            (
                old_row.id if old_row is not None else None,
                part_change_order_index.get(part_number, 0),
            )
        )

    results = die.insert_for_engineering_change(db, specs, current_user)
    links: list[EngineeringChangeEffectLinkInsert] = []
    sort_no = sort_no_start
    for result, (before_id, change_order_index) in zip(results, link_meta, strict=True):
        links.append(
            EngineeringChangeEffectLinkInsert(
                change_order_id=change_order_index,
                effect_kind=EFFECT_DIE_PART,
                before_id=before_id,
                after_id=result.part_id,
                sort_no=sort_no,
            )
        )
        sort_no += 1
    return links, len(results), warnings


def _find_letter_predecessor(
    existing: dict[str, EngineeringChangeDieAsOfRow], new_number: str
) -> EngineeringChangeDieAsOfRow | None:
    pred = find_letter_predecessor_number(existing.keys(), new_number)
    if pred is None:
        return None
    return existing.get(pred)
