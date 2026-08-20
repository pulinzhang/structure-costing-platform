"""BOM Repository - 数据访问"""

from typing import TypedDict

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from app.models.bom import BomNode, BomSnapshot
from app.repositories.persist import model_from_payload
from app.schemas.dto.bom_dto import BomNodeWrite, BomSnapshotWrite


class BomSnapshotListSummary(TypedDict):
    """BOM 清单列表 HUD 汇总。"""

    total_count: int
    active_count: int
    draft_count: int
    archived_count: int
    total_node_count: int


class BomSnapshotListFilters(TypedDict):
    """BOM 清单列表筛选体。"""

    locations: list[str]
    vehicle_models: list[str]
    bom_versions: list[str]
    statuses: list[str]
    summary: BomSnapshotListSummary


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

    def list_by_location_model(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
    ) -> list[BomSnapshot]:
        """同基地+车型下的全部 BOM 版本（新→旧）。"""
        return (
            db.query(BomSnapshot)
            .filter(
                BomSnapshot.location == location,
                BomSnapshot.vehicle_model == vehicle_model,
            )
            .order_by(BomSnapshot.id.desc())
            .all()
        )

    def paginate(
        self,
        db: Session,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomSnapshot], int]:
        q = self._apply_list_filters(
            db.query(BomSnapshot),
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            status=status,
        )

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

    def summarize(
        self,
        db: Session,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        status: str | None = None,
    ) -> BomSnapshotListSummary:
        """按当前筛选统计清单条数与节点总量（HUD）。"""
        q = self._apply_list_filters(
            db.query(BomSnapshot),
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            status=status,
        )
        rows = q.all()
        total_count = len(rows)
        active_count = sum(1 for row in rows if row.status == "active")
        draft_count = sum(1 for row in rows if row.status == "draft")
        archived_count = sum(1 for row in rows if row.status == "archived")
        snapshot_ids = [row.id for row in rows]
        total_node_count = 0
        if snapshot_ids:
            total_node_count = (
                db.query(func.count(BomNode.id))
                .filter(BomNode.snapshot_id.in_(snapshot_ids))
                .scalar()
                or 0
            )
        return {
            "total_count": total_count,
            "active_count": active_count,
            "draft_count": draft_count,
            "archived_count": archived_count,
            "total_node_count": int(total_node_count),
        }

    @staticmethod
    def _apply_list_filters(
        q: Query[BomSnapshot],
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        status: str | None = None,
    ) -> Query[BomSnapshot]:
        if location:
            q = q.filter(BomSnapshot.location == location)
        if vehicle_model:
            q = q.filter(BomSnapshot.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(BomSnapshot.bom_version == bom_version)
        if status:
            q = q.filter(BomSnapshot.status == status)
        return q

    def count_nodes(self, db: Session, snapshot_id: int) -> int:
        return (
            db.query(func.count(BomNode.id))
            .filter(BomNode.snapshot_id == snapshot_id)
            .scalar()
            or 0
        )

    def list_bom_versions(self, db: Session) -> list[str]:
        rows = (
            db.query(BomSnapshot.bom_version)
            .distinct()
            .order_by(BomSnapshot.bom_version.desc())
            .all()
        )
        return [r[0] for r in rows if r[0]]

    def list_statuses(self, db: Session) -> list[str]:
        rows = (
            db.query(BomSnapshot.status)
            .distinct()
            .order_by(BomSnapshot.status)
            .all()
        )
        return [r[0] for r in rows if r[0]]

    def create(
        self, db: Session, data: BomSnapshotWrite
    ) -> BomSnapshot:
        row = model_from_payload(BomSnapshot, data)
        db.add(row)
        db.flush()
        db.refresh(row)
        return row

    def delete(self, db: Session, snapshot: BomSnapshot) -> None:
        db.delete(snapshot)
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

    def get_cascade_filter_options(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        status: str | None = "active",
    ) -> dict[str, list[str]]:
        """
        材料清单级联：
        - 基地：全量
        - 项目：按基地过滤
        - 版本：按基地 + 项目过滤
        """
        location = (location or "").strip() or None
        vehicle_model = (vehicle_model or "").strip() or None
        status = (status or "").strip() or None
        if status in ("*", "__all__"):
            status = None

        loc_q = db.query(BomSnapshot.location).distinct()
        if status is not None:
            loc_q = loc_q.filter(BomSnapshot.status == status)
        locations = [
            row[0]
            for row in loc_q.order_by(BomSnapshot.location).all()
            if row[0]
        ]

        model_q = db.query(BomSnapshot.vehicle_model).distinct()
        if status is not None:
            model_q = model_q.filter(BomSnapshot.status == status)
        if location is not None:
            model_q = model_q.filter(BomSnapshot.location == location)
        vehicle_models = [
            row[0]
            for row in model_q.order_by(BomSnapshot.vehicle_model).all()
            if row[0]
        ]

        version_q = db.query(BomSnapshot.bom_version).distinct()
        if status is not None:
            version_q = version_q.filter(BomSnapshot.status == status)
        if location is not None:
            version_q = version_q.filter(BomSnapshot.location == location)
        if vehicle_model is not None:
            version_q = version_q.filter(BomSnapshot.vehicle_model == vehicle_model)
        bom_versions = [
            row[0]
            for row in version_q.order_by(BomSnapshot.bom_version.desc()).all()
            if row[0]
        ]

        return {
            "locations": locations,
            "vehicle_models": vehicle_models,
            "bom_versions": bom_versions,
        }


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

    def create(
        self, db: Session, data: BomNodeWrite
    ) -> BomNode:
        row = model_from_payload(BomNode, data)
        db.add(row)
        db.flush()
        db.refresh(row)
        return row

    def delete(self, db: Session, node: BomNode) -> None:
        db.delete(node)
        db.flush()

    def delete_by_snapshot(
        self, db: Session, snapshot_id: int
    ) -> int:
        count = (
            db.query(BomNode)
            .filter(BomNode.snapshot_id == snapshot_id)
            .delete(synchronize_session=False)
        )
        db.flush()
        return count
