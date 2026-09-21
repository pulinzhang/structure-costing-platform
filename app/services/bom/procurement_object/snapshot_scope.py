"""按 snapshot 头三键找材料清单（生成 / 供应商批传 / 覆盖检查共用）。

唯一取件：get_by_unique_key。禁止第二套查找；禁止 L0/EC。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.exceptions.base import NotFoundException
from app.models.bom.node import BomSnapshot
from app.repositories.bom.bom.snapshot import BomSnapshotRepository


def lookup_snapshot(
    db: Session,
    *,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> BomSnapshot | None:
    """精确匹配。调用方须已 normalize / 规范名；禁止在此 expand 别名。"""
    return BomSnapshotRepository().get_by_unique_key(db, location, vehicle_model, bom_version)


def require_snapshot(
    db: Session,
    *,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> BomSnapshot:
    snapshot = lookup_snapshot(
        db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
    )
    if snapshot is None:
        raise NotFoundException("未找到对应材料清单")
    return snapshot
