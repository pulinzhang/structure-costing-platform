"""本树焊接拆解：从旧树已有结果抄插（禁止按焊信重拆）。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import (
    CHANGE_TYPE_STOP,
    EFFECT_WELDING_BREAKDOWN,
    require_after_assembly_node,
)
from app.parsers.engineering_change.change_order_parser import ChangeOrderRowParsed
from app.repositories.engineering_change.effect_link_repository import (
    EngineeringChangeEffectLinkInsert,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.engineering import BomEngineeringService
from app.services.bom.welding_process_breakdown.service import BomWeldingProcessBreakdownService


@dataclass(slots=True)
class BreakdownPersistResult:
    inserted_count: int
    effect_links: list[EngineeringChangeEffectLinkInsert] = field(default_factory=list)


def persist_breakdown(
    db: Session,
    *,
    change_order: ChangeOrderRowParsed,
    after_root_id: int | None,
    source_id_remap: dict[int, int],
    current_user: UserVO,
    sort_no_start: int = 0,
    change_order_id: int = 0,
) -> BreakdownPersistResult:
    if change_order.change_type == CHANGE_TYPE_STOP:
        return BreakdownPersistResult(inserted_count=0)
    node = require_after_assembly_node(
        None if after_root_id is None else BomEngineeringService().get_node_row(db, after_root_id),
        part_number=change_order.after_assembly_part_number,
    )

    breakdown_ids = BomWeldingProcessBreakdownService().copy_for_new_tree(
        db,
        snapshot_id=node.snapshot_id,
        source_id_remap=source_id_remap,
        current_user=current_user,
    )
    links: list[EngineeringChangeEffectLinkInsert] = [
        EngineeringChangeEffectLinkInsert(
            change_order_id=change_order_id,
            effect_kind=EFFECT_WELDING_BREAKDOWN,
            before_id=None,
            after_id=breakdown_id,
            sort_no=sort_no_start + index,
        )
        for index, breakdown_id in enumerate(breakdown_ids)
    ]
    return BreakdownPersistResult(
        inserted_count=len(breakdown_ids),
        effect_links=links,
    )
