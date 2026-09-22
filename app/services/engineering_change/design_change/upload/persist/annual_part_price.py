"""
工程变更年度零件价：种树 remap 中零件号变了则 year>=生效年抄到新号。

旧行不动；新号同年键已有则跳过。只 flush。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import EFFECT_ANNUAL_PART_PRICE
from app.repositories.engineering_change.design_change.effect_link_repository import (
    EngineeringChangeEffectLinkInsert,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.annual_part_price.service import BomAnnualPartPriceService
from app.services.bom.bom.engineering import BomEngineeringService


def persist_annual_part_prices(
    db: Session,
    *,
    source_id_remaps: list[tuple[dict[int, int], int]],
    effective_year: int,
    location: str,
    current_user: UserVO,
    sort_no_start: int,
) -> list[EngineeringChangeEffectLinkInsert]:
    """source_id_remaps：各棵新树的（旧节点id→新节点id，变更单行下标）。"""
    revise_old_to_new, part_change_order_index = _changed_part_numbers(db, source_id_remaps)
    if not revise_old_to_new:
        return []

    service = BomAnnualPartPriceService()
    links: list[EngineeringChangeEffectLinkInsert] = []
    sort_no = sort_no_start
    for old_number, new_number in revise_old_to_new.items():
        results = service.clone_revise_for_engineering_change(
            db,
            location=location,
            old_part_number=old_number,
            new_part_number=new_number,
            from_year=effective_year,
            current_user=current_user,
        )
        for result in results:
            links.append(
                EngineeringChangeEffectLinkInsert(
                    change_order_id=part_change_order_index.get(new_number, 0),
                    effect_kind=EFFECT_ANNUAL_PART_PRICE,
                    before_id=result.before_id,
                    after_id=result.after_id,
                    sort_no=sort_no,
                )
            )
            sort_no += 1
    return links


def _changed_part_numbers(
    db: Session,
    source_id_remaps: list[tuple[dict[int, int], int]],
) -> tuple[dict[str, str], dict[str, int]]:
    revise_old_to_new: dict[str, str] = {}
    part_change_order_index: dict[str, int] = {}
    bom = BomEngineeringService()
    for source_id_remap, change_order_index in source_id_remaps:
        if not source_id_remap:
            continue
        node_ids = list(source_id_remap.keys()) + list(source_id_remap.values())
        rows = bom.list_node_rows_by_ids(db, node_ids)
        by_id = {int(row.id): row for row in rows}
        for old_id, new_id in source_id_remap.items():
            old_row = by_id.get(int(old_id))
            new_row = by_id.get(int(new_id))
            if old_row is None or new_row is None:
                continue
            old_number = (old_row.part_number or "").strip()
            new_number = (new_row.part_number or "").strip()
            if not old_number or not new_number or old_number == new_number:
                continue
            revise_old_to_new[old_number] = new_number
            part_change_order_index[new_number] = change_order_index
    return revise_old_to_new, part_change_order_index
