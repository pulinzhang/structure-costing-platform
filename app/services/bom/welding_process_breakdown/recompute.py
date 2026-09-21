"""
编辑后重算衍生字段（rollup / 子件用量校验）

生成时与手工改量后共用，避免核对态撒谎。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.services.bom.bom.period import BomPeriodService
from app.services.bom.welding_process_breakdown.bom_tree import build_children_map
from app.services.bom.welding_process_breakdown.fastener_check import (
    check_process_qty_against_children,
)
from app.services.bom.welding_process_breakdown.rollup import apply_rollup_flags


def recompute_scope_derived_fields(
    db: Session,
    *,
    repository: BomWeldingProcessBreakdownRepository,
    location: str,
    vehicle_model: str,
    bom_version: str,
    snapshot_id: int | None,
) -> None:
    """
    就地刷新范围内全部明细的 qty_check_* 与 rollup_flag。

    调用方负责 commit。无 snapshot 时仅重置 rollup 为 own（无法对照 BOM）。
    """
    nodes = repository.list_by_scope(
        db,
        location=location,
        vehicle_model=vehicle_model,
        source_node_ids=BomPeriodService().node_ids_for_l0_version(
            db,
            bom_version=bom_version,
            location=location,
            vehicle_model=vehicle_model,
        ),
    )
    if not nodes:
        return

    for node in nodes:
        for line in node.lines:
            line.rollup_flag = "own"

    if not snapshot_id:
        return

    bom_nodes = BomNodeRepository().list_by_snapshot(db, snapshot_id)
    children_map = build_children_map(bom_nodes)
    source_to_breakdown: dict[int, Any] = {
        node.source_node_id: node for node in nodes if node.source_node_id is not None
    }

    for node in nodes:
        if node.source_node_id is None:
            continue
        children = children_map.get(node.source_node_id, [])
        for line in node.lines:
            qty_check = check_process_qty_against_children(
                process_token=line.process_token,
                process_qty=line.process_qty,
                children=children,
            )
            line.child_fastener_qty_sum = qty_check.child_fastener_qty_sum
            line.qty_check_status = qty_check.qty_check_status
            line.qty_check_detail = qty_check.qty_check_detail

    apply_rollup_flags(nodes, source_to_breakdown, children_map)
