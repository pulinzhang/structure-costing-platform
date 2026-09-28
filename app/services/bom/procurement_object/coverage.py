"""采购对象覆盖检查（引擎按 snapshot 版本；总成 as_of 齐套在 assembly ready 内按同口径判定）。"""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.services.bom.procurement_object.classify import SECTION_OBJECT, classify_nodes
from app.services.bom.procurement_object.snapshot_scope import lookup_snapshot


class ProcurementObjectCoverage(NamedTuple):
    complete: bool
    message: str
    object_count: int
    expected_count: int


def evaluate_procurement_object_coverage(
    db: Session,
    *,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> ProcurementObjectCoverage:
    """该 snapshot 是否已有齐套采购对象行（相对 classify 应列入集合）。"""
    location = location.strip()
    vehicle_model = vehicle_model.strip()
    bom_version = bom_version.strip()
    snapshot = lookup_snapshot(
        db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
    )
    if snapshot is None:
        return ProcurementObjectCoverage(False, "未找到对应材料清单，请先上传 BOM", 0, 0)

    nodes = BomNodeRepository().list_by_snapshot(db, snapshot.id)
    classified = classify_nodes(nodes)
    expected_ids = {
        int(row.source_node_id) for row in classified.rows if row.section == SECTION_OBJECT
    }
    expected_count = len(expected_ids)
    if expected_count == 0:
        return ProcurementObjectCoverage(True, "该版本无采购对象列入项", 0, 0)

    list_header = BomProcurementObjectRepository().get_list_by_snapshot_id(db, snapshot.id)
    if list_header is None:
        return ProcurementObjectCoverage(False, "请先生成采购对象列表", 0, expected_count)

    objects = BomProcurementObjectRepository().list_objects_by_list_id(db, list_header.id)
    present_ids = {
        int(obj.source_node_id)
        for obj in objects
        if obj.section == SECTION_OBJECT and obj.source_node_id is not None
    }
    object_count = len(present_ids)
    missing = expected_ids - present_ids
    if missing:
        return ProcurementObjectCoverage(
            False,
            f"采购对象未齐（应列入 {expected_count}，现有 {object_count}），请重新生成",
            object_count,
            expected_count,
        )
    return ProcurementObjectCoverage(True, "采购对象已齐", object_count, expected_count)
