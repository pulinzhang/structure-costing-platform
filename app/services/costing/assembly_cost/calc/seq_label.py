"""计算报告序号：与采购协议同一套规则。"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bom.node import BomNode
from app.models.bom.procurement_object import BomProcurementObject
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.schemas.vo.assembly_cost_vo import AssemblyCostCalcCardTraceVO, AssemblyCostCalcLogVO
from app.services.bom.procurement_object.classify import SECTION_OBJECT
from app.services.costing.procurement_contract_report.assemble import (
    PrepRow,
    assign_seq_labels,
    prep_fields_from_node,
    seq_sort_key,
)
from app.services.costing.procurement_contract_report.qty import l0_node_of


def calc_card_seq_labels(
    nodes: Sequence[BomNode],
    objects: Sequence[BomProcurementObject],
    subject_ids: set[int],
) -> dict[int, str]:
    nodes_by_id = {node.id: node for node in nodes}
    po_rows: list[PrepRow] = []
    for item in objects:
        if item.section != SECTION_OBJECT:
            continue
        node = nodes_by_id.get(item.source_node_id)
        l0 = l0_node_of(item.source_node_id, nodes_by_id)
        l0_node_id = l0.id if l0 is not None else item.source_node_id
        l0_seq_no = l0.seq_no if l0 is not None else None
        level, excel_row, sort_no = prep_fields_from_node(node, fallback_excel_row=item.excel_row)
        po_rows.append(
            PrepRow(
                source_node_id=item.source_node_id,
                part_number=item.part_number,
                part_name=item.part_name,
                internal_number=item.internal_number,
                supplier_name=item.supplier_name,
                object_kind=item.object_kind,
                l0_node_id=l0_node_id,
                l0_part_number=item.l0_part_number,
                l0_seq_no=l0_seq_no,
                sort_no=sort_no,
                excel_row=excel_row,
                level=level,
                vehicle_qty=Decimal("0"),
                month_amounts=[],
            )
        )
    assign_seq_labels(po_rows)
    labels = {row.source_node_id: row.seq_label for row in po_rows}
    for node_id in subject_ids:
        if node_id in labels:
            continue
        node = nodes_by_id.get(node_id)
        if node is None or node.parent_id is not None:
            continue
        labels[node_id] = "" if node.seq_no is None else str(node.seq_no)
    return labels


def attach_calc_card_seq_labels(db: Session, vo: AssemblyCostCalcLogVO) -> None:
    """旧日志没有序号时，按当前 BOM / 采购对象补上。"""
    if not vo.cards:
        return
    if vo.bom_version:
        snap = BomSnapshotRepository().get_by_unique_key(
            db, vo.location, vo.vehicle_model, vo.bom_version
        )
        nodes = BomNodeRepository().list_by_snapshot(db, snap.id) if snap is not None else []
        # calc 日志 bom_version = snapshot SOP 字，与清单头键同形；不是列表浏览筛
        header = BomProcurementObjectRepository().get_list_by_scope(
            db,
            location=vo.location,
            vehicle_model=vo.vehicle_model,
            bom_version=vo.bom_version,
        )
        objects: list[BomProcurementObject] = []
        if header is not None:
            objects = BomProcurementObjectRepository().list_objects_by_list_id(db, header.id)
    else:
        nodes = BomNodeRepository().list_by_location_vehicle(
            db, location=vo.location, vehicle_model=vo.vehicle_model
        )
        objects = BomProcurementObjectRepository().list_objects_by_location_vehicle(
            db, location=vo.location, vehicle_model=vo.vehicle_model
        )
    if not nodes:
        _sort_cards(vo.cards)
        return
    labels = calc_card_seq_labels(nodes, objects, {node.id for node in nodes})
    by_root_part: dict[str, str] = {}
    by_part_kind: dict[tuple[str, str | None], str] = {}
    by_part: dict[str, str] = {}
    for node in nodes:
        label = labels.get(node.id)
        if not label:
            continue
        if node.parent_id is None:
            by_root_part.setdefault(node.part_number, label)
        by_part.setdefault(node.part_number, label)
    for item in objects:
        if item.section != SECTION_OBJECT:
            continue
        label = labels.get(item.source_node_id)
        if not label:
            continue
        by_part_kind.setdefault((item.part_number, item.object_kind), label)
        by_part.setdefault(item.part_number, label)
    for card in vo.cards:
        if card.source_node_id is not None and card.source_node_id in labels:
            card.seq_label = labels[card.source_node_id]
            continue
        if card.seq_label:
            continue
        if card.is_tree_root:
            card.seq_label = by_root_part.get(card.part_number, "")
        else:
            card.seq_label = by_part_kind.get(
                (card.part_number, card.object_kind),
                by_part.get(card.part_number, ""),
            )
    _sort_cards(vo.cards)


def _sort_cards(cards: list[AssemblyCostCalcCardTraceVO]) -> None:
    cards.sort(key=lambda card: (*seq_sort_key(card.seq_label or ""), card.part_number))
