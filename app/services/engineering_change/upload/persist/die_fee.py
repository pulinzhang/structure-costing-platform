"""
工程变更模具费结果：改图有 year>=生效年结果则抄到新号。

绑新布点 id；旧行不动；新号同年键已有则跳过。只 flush。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import EFFECT_DIE_FEE
from app.repositories.engineering_change.effect_link_repository import (
    EngineeringChangeEffectLinkInsert,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.die_fee.die_fee_service import StampingDieFeeService


def persist_die_fees(
    db: Session,
    *,
    revise_old_to_new: dict[str, str],
    part_change_order_index: dict[str, int],
    new_die_part_ids: dict[str, int],
    effective_year: int,
    location: str,
    vehicle_model: str,
    current_user: UserVO,
    sort_no_start: int,
) -> list[EngineeringChangeEffectLinkInsert]:
    """返回效果链接（sort_no 从 sort_no_start 起）。"""
    if not revise_old_to_new:
        return []

    service = StampingDieFeeService()
    links: list[EngineeringChangeEffectLinkInsert] = []
    sort_no = sort_no_start
    for old_number, new_number in revise_old_to_new.items():
        if not new_number:
            continue
        results = service.clone_revise_for_engineering_change(
            db,
            location=location,
            vehicle_model=vehicle_model,
            old_part_number=old_number,
            new_part_number=new_number,
            from_year=effective_year,
            new_die_part_id=new_die_part_ids.get(new_number),
            current_user=current_user,
        )
        for result in results:
            links.append(
                EngineeringChangeEffectLinkInsert(
                    change_order_id=part_change_order_index.get(new_number, 0),
                    effect_kind=EFFECT_DIE_FEE,
                    before_id=result.before_id,
                    after_id=result.after_id,
                    sort_no=sort_no,
                )
            )
            sort_no += 1
    return links
