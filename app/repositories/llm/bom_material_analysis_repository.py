"""材料清单（BOM 节点）— LLM 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment, pick_part_row
from app.models.bom.node import BomNode, BomSnapshot


def _normalize_location(location: str | None) -> str | None:
    if not location:
        return None
    text = location.strip()
    if text.endswith("基地"):
        return text[:-2]
    return text


@dataclass(frozen=True, slots=True)
class BomMaterialNodeRow:
    snapshot_id: int
    location: str
    vehicle_model: str
    bom_version: str
    part_number: str
    part_name: str | None
    level: int
    node_role: str
    material: str | None
    thickness_mm: Decimal | None
    qty: Decimal | None


class BomMaterialAnalysisRepository:
    def query_node_rows(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        limit: int = 5000,
    ) -> list[BomMaterialNodeRow]:
        q = db.query(BomNode, BomSnapshot).join(
            BomSnapshot, BomNode.snapshot_id == BomSnapshot.id
        )
        normalized = _normalize_location(location)
        if normalized:
            q = q.filter(BomSnapshot.location == normalized)
        if vehicle_model:
            q = q.filter(BomSnapshot.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(BomSnapshot.bom_version == bom_version)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(BomNode.part_number.like(pattern, escape="\\"))

        q = q.order_by(
            BomSnapshot.location.asc(),
            BomSnapshot.vehicle_model.asc(),
            BomSnapshot.bom_version.asc(),
            BomNode.sort_no.asc(),
        ).limit(limit)

        return [
            BomMaterialNodeRow(
                snapshot_id=int(snapshot.id),
                location=str(snapshot.location),
                vehicle_model=str(snapshot.vehicle_model),
                bom_version=str(snapshot.bom_version),
                part_number=str(node.part_number),
                part_name=node.part_name,
                level=int(node.level),
                node_role=str(node.node_role),
                material=node.material,
                thickness_mm=(
                    Decimal(str(node.thickness_mm))
                    if node.thickness_mm is not None
                    else None
                ),
                qty=Decimal(str(node.qty)) if node.qty is not None else None,
            )
            for node, snapshot in q.all()
        ]

    def pick_best_row(
        self,
        rows: list[BomMaterialNodeRow],
        *,
        part_token: str,
    ) -> BomMaterialNodeRow | None:
        if not rows:
            return None
        picked = pick_part_row(
            rows,
            part_token,
            get_part_number=lambda row: row.part_number,
        )
        return picked if isinstance(picked, BomMaterialNodeRow) else rows[0]
