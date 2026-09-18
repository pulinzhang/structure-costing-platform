"""
合册模具布点按变更单逻辑建立，不读 Excel。

改图且变更前零件有仍有效布点：旧行到期到前一月，整行抄出新号（含 alloc_ratio）。
无旧布点、增加零件、完成停止、此件不装：不建。简图不从「零件汇总」抽；
工艺确认表简图已写入新号工艺行，模具清单按零件号对上同一张图。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.engineering_change_gates import EFFECT_DIE_PART
from app.common.period import previous_month
from app.repositories.engineering_change.effect_link_repository import (
    EngineeringChangeEffectLinkInsert,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.die.die_service import StampingDieService
from app.services.stamping.die.engineering_change import EngineeringChangeDiePartSpec


def persist_die_parts(
    db: Session,
    *,
    revise_old_to_new: dict[str, str],
    part_change_order_index: dict[str, int],
    effective_year: int,
    effective_month: int,
    location: str,
    vehicle_model: str,
    current_user: UserVO,
    sort_no_start: int,
    version: str | None = None,
    expiry_year: int | None = None,
    expiry_month: int | None = None,
) -> tuple[list[EngineeringChangeEffectLinkInsert], int]:
    """布点不读 Excel。返回 (效果链接, 新插入件数)。"""
    if not revise_old_to_new:
        return [], 0

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

    specs: list[EngineeringChangeDiePartSpec] = []
    change_order_indexes: list[int] = []
    for old_number, new_number in revise_old_to_new.items():
        if not new_number or new_number in existing_by_number:
            continue
        old_row = existing_by_number.get(old_number)
        if old_row is None:
            continue
        specs.append(
            die.clone_revise_for_engineering_change(
                db,
                predecessor_id=old_row.id,
                new_part_number=new_number,
                version=version,
                effective_year=effective_year,
                effective_month=effective_month,
                expiry_year=expiry_year,
                expiry_month=expiry_month,
                predecessor_expiry_year=prev_year,
                predecessor_expiry_month=prev_month,
                created_by=str(audit["created_by"] or ""),
                updated_by=str(audit["updated_by"] or ""),
            )
        )
        change_order_indexes.append(part_change_order_index.get(new_number, 0))

    if not specs:
        return [], 0

    results = die.insert_for_engineering_change(db, specs, current_user)
    links: list[EngineeringChangeEffectLinkInsert] = []
    sort_no = sort_no_start
    for result, change_order_index in zip(results, change_order_indexes, strict=True):
        links.append(
            EngineeringChangeEffectLinkInsert(
                change_order_id=change_order_index,
                effect_kind=EFFECT_DIE_PART,
                before_id=result.predecessor_id,
                after_id=result.part_id,
                sort_no=sort_no,
            )
        )
        sort_no += 1
    return links, len(results)
