"""BOM 树节点行数据访问（不含树期过滤）。"""

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql.elements import ColumnElement

from app.common.bom.node_order import bom_node_sql_order
from app.models.bom import BomNode, BomSnapshot
from app.repositories.persist import model_from_payload
from app.schemas.dto.bom_dto import BomNodeWrite

_BOM_NODE_ORDER = bom_node_sql_order(BomNode)


class BomNodeRepository:
    """BOM 树节点数据访问"""

    def get_by_id(self, db: Session, node_id: int) -> BomNode | None:
        return db.query(BomNode).filter(BomNode.id == node_id).first()

    def list_by_snapshot(self, db: Session, snapshot_id: int) -> list[BomNode]:
        return (
            db.query(BomNode)
            .filter(BomNode.snapshot_id == snapshot_id)
            .order_by(*_BOM_NODE_ORDER)
            .all()
        )

    def list_by_location_vehicle(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[BomNode]:
        return (
            db.query(BomNode)
            .filter(
                BomNode.location == location,
                BomNode.vehicle_model == vehicle_model,
            )
            .order_by(*_BOM_NODE_ORDER)
            .all()
        )

    def create(self, db: Session, data: BomNodeWrite) -> BomNode:
        snapshot = db.query(BomSnapshot).filter(BomSnapshot.id == data.snapshot_id).first()
        if snapshot is not None and not data.location:
            data.location = snapshot.location
            data.vehicle_model = snapshot.vehicle_model
            data.bom_version = snapshot.bom_version
        row = model_from_payload(BomNode, data)
        db.add(row)
        db.flush()
        db.refresh(row)
        return row

    def get_l0_by_part_number(
        self, db: Session, snapshot_id: int, part_number: str
    ) -> BomNode | None:
        return (
            db.query(BomNode)
            .filter(
                BomNode.snapshot_id == snapshot_id,
                BomNode.level == 0,
                BomNode.part_number == part_number,
            )
            .first()
        )

    def list_l0(self, db: Session, snapshot_id: int) -> list[BomNode]:
        return (
            db.query(BomNode)
            .filter(BomNode.snapshot_id == snapshot_id, BomNode.level == 0)
            .order_by(*_BOM_NODE_ORDER)
            .all()
        )

    def delete_descendants(self, db: Session, snapshot_id: int, root_id: int) -> None:
        rows = self.list_by_snapshot(db, snapshot_id)
        children_of: dict[int, list[int]] = {}
        for row in rows:
            if row.parent_id is None:
                continue
            children_of.setdefault(row.parent_id, []).append(row.id)
        to_delete: list[int] = []
        stack = list(children_of.get(root_id, []))
        while stack:
            current = stack.pop()
            to_delete.append(current)
            stack.extend(children_of.get(current, []))
        if not to_delete:
            return
        db.query(BomNode).filter(BomNode.id.in_(to_delete)).delete(synchronize_session=False)
        db.flush()

    def delete(self, db: Session, node: BomNode) -> None:
        db.delete(node)
        db.flush()

    def list_where_used_hits(
        self,
        db: Session,
        *,
        locations: list[str] | None,
        vehicle_model: str | None,
        bom_version: str | None,
        statuses: list[str] | None,
        part_number_like: str | None,
        part_name_like: str | None,
        internal_number: str | None,
        fetch_limit: int,
    ) -> list[BomNode]:
        q = (
            db.query(BomNode)
            .join(BomSnapshot, BomSnapshot.id == BomNode.snapshot_id)
            .options(joinedload(BomNode.snapshot))
        )
        if locations:
            q = q.filter(BomSnapshot.location.in_(locations))
        if vehicle_model:
            q = q.filter(BomSnapshot.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(BomSnapshot.bom_version == bom_version)
        if statuses:
            q = q.filter(BomSnapshot.status.in_(statuses))
        identity_filters: list[ColumnElement[bool]] = []
        if part_number_like:
            identity_filters.append(
                func.upper(BomNode.part_number).like(part_number_like, escape="\\")
            )
        if part_name_like:
            identity_filters.append(BomNode.part_name.like(part_name_like, escape="\\"))
        if internal_number is not None:
            identity_filters.append(func.trim(BomNode.internal_number) == internal_number)
        if not identity_filters:
            return []
        q = q.filter(or_(*identity_filters))
        return (
            q.order_by(BomNode.snapshot_id.asc(), BomNode.sort_no.asc(), BomNode.id.asc())
            .limit(fetch_limit)
            .all()
        )

    def list_by_ids(self, db: Session, node_ids: list[int]) -> list[BomNode]:
        if not node_ids:
            return []
        unique_ids = list(dict.fromkeys(node_ids))
        rows: list[BomNode] = []
        chunk_size = 500
        for offset in range(0, len(unique_ids), chunk_size):
            chunk = unique_ids[offset : offset + chunk_size]
            rows.extend(
                db.query(BomNode)
                .options(joinedload(BomNode.snapshot))
                .filter(BomNode.id.in_(chunk))
                .all()
            )
        by_id = {row.id: row for row in rows}
        return [by_id[node_id] for node_id in unique_ids if node_id in by_id]

    def list_l0_with_seq_by_locations(
        self,
        db: Session,
        *,
        locations: list[str],
        vehicle_model: str,
    ) -> list[BomNode]:
        if not locations:
            return []
        return (
            db.query(BomNode)
            .filter(
                BomNode.level == 0,
                BomNode.location.in_(locations),
                BomNode.vehicle_model == vehicle_model,
                BomNode.seq_no.isnot(None),
            )
            .all()
        )
