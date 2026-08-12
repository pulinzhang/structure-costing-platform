"""BOM Repository - 数据访问"""

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.bom import BomNode, BomSnapshot


class BomSnapshotRepository:
    """BOM 清单版本数据访问"""

    def get_by_id(self, db: Session, snapshot_id: int) -> BomSnapshot | None:
        return db.query(BomSnapshot).filter(BomSnapshot.id == snapshot_id).first()

    def get_by_unique_key(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomSnapshot | None:
        return (
            db.query(BomSnapshot)
            .filter(
                BomSnapshot.location == location,
                BomSnapshot.vehicle_model == vehicle_model,
                BomSnapshot.bom_version == bom_version,
            )
            .first()
        )

    def paginate(
        self,
        db: Session,
        location: str | None = None,
        vehicle_model: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomSnapshot], int]:
        q = db.query(BomSnapshot)
        if location:
            q = q.filter(BomSnapshot.location == location)
        if vehicle_model:
            q = q.filter(BomSnapshot.vehicle_model == vehicle_model)
        if status:
            q = q.filter(BomSnapshot.status == status)

        total = q.count()
        rows = (
            q.order_by(
                BomSnapshot.vehicle_model,
                BomSnapshot.location,
                BomSnapshot.bom_version.desc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def count_nodes(self, db: Session, snapshot_id: int) -> int:
        return (
            db.query(func.count(BomNode.id))
            .filter(BomNode.snapshot_id == snapshot_id)
            .scalar()
            or 0
        )

    def create(self, db: Session, data: dict[str, Any], *, commit: bool = True) -> BomSnapshot:
        row = BomSnapshot(**data)
        db.add(row)
        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
        return row

    def delete(self, db: Session, snapshot: BomSnapshot, *, commit: bool = True) -> None:
        db.delete(snapshot)
        if commit:
            db.commit()
        else:
            db.flush()

    def list_locations(self, db: Session) -> list[str]:
        rows = (
            db.query(BomSnapshot.location)
            .distinct()
            .order_by(BomSnapshot.location)
            .all()
        )
        return [r[0] for r in rows if r[0]]

    def list_vehicle_models(self, db: Session) -> list[str]:
        rows = (
            db.query(BomSnapshot.vehicle_model)
            .distinct()
            .order_by(BomSnapshot.vehicle_model)
            .all()
        )
        return [r[0] for r in rows if r[0]]


class BomNodeRepository:
    """BOM 树节点数据访问"""

    def get_by_id(self, db: Session, node_id: int) -> BomNode | None:
        return db.query(BomNode).filter(BomNode.id == node_id).first()

    def list_by_snapshot(self, db: Session, snapshot_id: int) -> list[BomNode]:
        return (
            db.query(BomNode)
            .filter(BomNode.snapshot_id == snapshot_id)
            .order_by(BomNode.level, BomNode.sort_no, BomNode.id)
            .all()
        )

    def create(self, db: Session, data: dict[str, Any], *, commit: bool = True) -> BomNode:
        row = BomNode(**data)
        db.add(row)
        if commit:
            db.commit()
            db.refresh(row)
        else:
            db.flush()
        return row

    def delete(self, db: Session, node: BomNode, *, commit: bool = True) -> None:
        db.delete(node)
        if commit:
            db.commit()
        else:
            db.flush()

    def delete_by_snapshot(
        self, db: Session, snapshot_id: int, *, commit: bool = True
    ) -> int:
        count = (
            db.query(BomNode)
            .filter(BomNode.snapshot_id == snapshot_id)
            .delete(synchronize_session=False)
        )
        if commit:
            db.commit()
        else:
            db.flush()
        return count
