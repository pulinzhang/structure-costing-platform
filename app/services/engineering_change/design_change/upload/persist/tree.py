"""工程变更种树 / 失效：仅调上游 BomEngineeringService（算法在 bom/bom/change_tree_plant）。"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.parsers.bom.bom_parser import BomParsedNode
from app.parsers.engineering_change.design_change.change_order_parser import ChangeOrderRowParsed
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.engineering import (
    BomChangePlantResult,
    BomChangePlantSpec,
    BomEngineeringService,
)


def change_order_to_plant_spec(change_order: ChangeOrderRowParsed) -> BomChangePlantSpec:
    """变更单解析结果 → BOM 种树规格（EC 适配，不进上游）。"""
    return BomChangePlantSpec(
        change_type=change_order.change_type,
        before_assembly_part_number=change_order.before_assembly_part_number,
        after_assembly_part_number=change_order.after_assembly_part_number,
        assembly_name=change_order.assembly_name,
        part_level=change_order.part_level,
        before_part_number=change_order.before_part_number,
        after_part_number=change_order.after_part_number,
        part_name=change_order.part_name,
    )


def expire_l0_tree(
    db: Session,
    *,
    l0_id: int,
    expiry_year: int,
    expiry_month: int,
    current_user: UserVO,
) -> None:
    """级联写失效月，不 commit（工程变更事务用）。"""
    BomEngineeringService().expire_l0_tree(
        db,
        root_id=l0_id,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        current_user=current_user,
    )


def plant_change_tree(
    db: Session,
    *,
    snapshot_id: int,
    location: str,
    vehicle_model: str,
    before_l0_id: int,
    seq_no: int | None,
    change_order: ChangeOrderRowParsed,
    parsed_nodes: list[BomParsedNode],
    extra_change_orders: Sequence[ChangeOrderRowParsed] = (),
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    current_user: UserVO,
    node_bom_version: str | None = None,
) -> BomChangePlantResult:
    """EC 适配：变更单 → BomChangePlantSpec，再调上游种树。"""
    return BomEngineeringService().plant_change_tree(
        db,
        snapshot_id=snapshot_id,
        location=location,
        vehicle_model=vehicle_model,
        before_l0_id=before_l0_id,
        seq_no=seq_no,
        spec=change_order_to_plant_spec(change_order),
        parsed_nodes=parsed_nodes,
        extra_specs=tuple(change_order_to_plant_spec(item) for item in extra_change_orders),
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        current_user=current_user,
        node_bom_version=node_bom_version,
    )
