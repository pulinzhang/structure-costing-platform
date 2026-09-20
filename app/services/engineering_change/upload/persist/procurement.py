"""本树采购对象插行。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.common.engineering_change_gates import (
    CHANGE_TYPE_STOP,
    EFFECT_PROCUREMENT_OBJECT,
    require_after_assembly_node,
)
from app.parsers.engineering_change.change_order_parser import ChangeOrderRowParsed
from app.repositories.engineering_change.effect_link_repository import (
    EngineeringChangeEffectLinkInsert,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.engineering import BomEngineeringService
from app.services.bom.procurement_object.service import BomProcurementObjectService


@dataclass(slots=True)
class ProcurementPersistResult:
    inserted_count: int
    effect_links: list[EngineeringChangeEffectLinkInsert] = field(default_factory=list)


def persist_procurement(
    db: Session,
    *,
    change_order: ChangeOrderRowParsed,
    after_root_id: int | None,
    current_user: UserVO,
    sort_no_start: int = 0,
    change_order_id: int = 0,
) -> ProcurementPersistResult:
    if change_order.change_type == CHANGE_TYPE_STOP:
        return ProcurementPersistResult(inserted_count=0)
    bom = BomEngineeringService()
    node = require_after_assembly_node(
        None if after_root_id is None else bom.get_node_row(db, after_root_id),
        part_number=change_order.after_assembly_part_number,
    )
    po_service = BomProcurementObjectService()
    old_l0 = bom.find_l0_by_part_number(
        db,
        location=node.location,
        vehicle_model=node.vehicle_model,
        part_number=change_order.before_assembly_part_number,
    )
    old_l0_id = old_l0.id if old_l0 is not None else None
    object_ids = po_service.insert_for_new_tree(
        db,
        snapshot_id=node.snapshot_id,
        new_l0_id=node.id,
        old_l0_id=old_l0_id,
        current_user=current_user,
    )
    links: list[EngineeringChangeEffectLinkInsert] = []
    sort_no = sort_no_start
    for object_id in object_ids:
        links.append(
            EngineeringChangeEffectLinkInsert(
                change_order_id=change_order_id,
                effect_kind=EFFECT_PROCUREMENT_OBJECT,
                before_id=None,
                after_id=object_id,
                sort_no=sort_no,
            )
        )
        sort_no += 1
    return ProcurementPersistResult(
        inserted_count=len(object_ids),
        effect_links=links,
    )
