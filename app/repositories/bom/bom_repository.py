"""BOM Repository - 数据访问"""

from typing import TypedDict

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Query, Session, joinedload
from sqlalchemy.sql.elements import ColumnElement

from app.common.bom.node_order import MISSING_SEQ_NO
from app.common.types.repository_types import BomCascadeFilterOptions
from app.models.bom import BomNode, BomSnapshot
from app.repositories.bom.period_trees import (
    nodes_in_as_of_trees,
    nodes_in_year_overlap_trees,
)
from app.repositories.period_query import period_hit_clause
from app.repositories.persist import model_from_payload
from app.schemas.dto.bom_dto import BomNodeWrite, BomSnapshotWrite

# seq_no → level → L0 零件号 → excel_row → part_number
_BOM_NODE_ORDER = (
    func.coalesce(BomNode.seq_no, MISSING_SEQ_NO),
    BomNode.level,
    case((BomNode.level == 0, BomNode.part_number), else_=""),
    func.coalesce(BomNode.excel_row, BomNode.sort_no, 0),
    BomNode.part_number,
    BomNode.sort_no,
    BomNode.id,
)


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


class BomL0ScopeRow(TypedDict):
    """含 L0 节点的 BOM 快照 scope（location 为快照上实际字符串）。"""

    location: str
    vehicle_model: str
    bom_version: str


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
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomSnapshot], int]:
        q = self._apply_list_filters(
            db.query(BomSnapshot),
            location=location,
            locations=locations,
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
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        status: str | None = None,
    ) -> BomSnapshotListSummary:
        """按当前筛选统计清单条数与节点总量（HUD）。"""
        q = self._apply_list_filters(
            db.query(BomSnapshot),
            location=location,
            locations=locations,
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
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        status: str | None = None,
    ) -> Query[BomSnapshot]:
        if locations is not None:
            q = q.filter(BomSnapshot.location.in_(locations))
        elif location:
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
            db.query(func.count(BomNode.id)).filter(BomNode.snapshot_id == snapshot_id).scalar()
            or 0
        )

    def count_all_nodes(
        self,
        db: Session,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
    ) -> int:
        """统计 BOM 节点总量（可按基地 / 车型过滤）。"""
        node_q = (
            db.query(func.count(BomNode.id))
            .select_from(BomNode)
            .join(BomSnapshot, BomSnapshot.id == BomNode.snapshot_id)
        )
        if locations is not None:
            node_q = node_q.filter(BomSnapshot.location.in_(locations))
        elif location:
            node_q = node_q.filter(BomSnapshot.location == location)
        if vehicle_model:
            node_q = node_q.filter(BomSnapshot.vehicle_model == vehicle_model)
        return int(node_q.scalar() or 0)

    def discover_l0_scopes(
        self,
        db: Session,
        locations: list[str],
        *,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
    ) -> list[BomL0ScopeRow]:
        """发现指定基地别名下含 L0 节点的 BOM 版本；可按 L0 月命中裁。"""
        if not locations:
            return []
        filters: list[ColumnElement[bool]] = [
            BomSnapshot.location.in_(locations),
            BomNode.level == 0,
        ]
        if as_of_year is not None and as_of_month is not None:
            filters.append(
                period_hit_clause(
                    BomNode.effective_year,
                    BomNode.effective_month,
                    BomNode.expiry_year,
                    BomNode.expiry_month,
                    as_of_year,
                    as_of_month,
                )
            )
        rows = (
            db.query(
                BomSnapshot.location,
                BomSnapshot.vehicle_model,
                BomSnapshot.bom_version,
            )
            .join(BomNode, BomNode.snapshot_id == BomSnapshot.id)
            .filter(*filters)
            .group_by(
                BomSnapshot.location,
                BomSnapshot.vehicle_model,
                BomSnapshot.bom_version,
            )
            .having(func.count(BomNode.id) > 0)
            .order_by(
                BomSnapshot.vehicle_model,
                BomSnapshot.bom_version,
            )
            .all()
        )
        scopes: list[BomL0ScopeRow] = []
        seen: set[tuple[str, str]] = set()
        for location, vehicle_model, bom_version in rows:
            vehicle = (vehicle_model or "").strip()
            version = (bom_version or "").strip()
            if not vehicle or not version:
                continue
            key = (vehicle, version)
            if key in seen:
                continue
            seen.add(key)
            scopes.append(
                {
                    "location": (location or "").strip(),
                    "vehicle_model": vehicle,
                    "bom_version": version,
                }
            )
        return scopes

    def list_bom_versions(self, db: Session) -> list[str]:
        rows = (
            db.query(BomSnapshot.bom_version)
            .distinct()
            .order_by(BomSnapshot.bom_version.desc())
            .all()
        )
        return [r[0] for r in rows if r[0]]

    def list_statuses(self, db: Session) -> list[str]:
        rows = db.query(BomSnapshot.status).distinct().order_by(BomSnapshot.status).all()
        return [r[0] for r in rows if r[0]]

    def create(self, db: Session, data: BomSnapshotWrite) -> BomSnapshot:
        row = model_from_payload(BomSnapshot, data)
        db.add(row)
        db.flush()
        db.refresh(row)
        return row

    def delete(self, db: Session, snapshot: BomSnapshot) -> None:
        db.delete(snapshot)
        db.flush()

    def list_locations(self, db: Session) -> list[str]:
        rows = db.query(BomSnapshot.location).distinct().order_by(BomSnapshot.location).all()
        return [r[0] for r in rows if r[0]]

    def list_vehicle_models(self, db: Session) -> list[str]:
        rows = (
            db.query(BomSnapshot.vehicle_model).distinct().order_by(BomSnapshot.vehicle_model).all()
        )
        return [r[0] for r in rows if r[0]]

    def get_cascade_filter_options(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        status: str | None = "active",
    ) -> BomCascadeFilterOptions:
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
        distinct_locations = [
            row[0] for row in loc_q.order_by(BomSnapshot.location).all() if row[0]
        ]

        model_q = db.query(BomSnapshot.vehicle_model).distinct()
        if status is not None:
            model_q = model_q.filter(BomSnapshot.status == status)
        if locations is not None:
            model_q = model_q.filter(BomSnapshot.location.in_(locations))
        elif location is not None:
            model_q = model_q.filter(BomSnapshot.location == location)
        vehicle_models = [
            row[0] for row in model_q.order_by(BomSnapshot.vehicle_model).all() if row[0]
        ]

        version_q = db.query(BomSnapshot.bom_version).distinct()
        if status is not None:
            version_q = version_q.filter(BomSnapshot.status == status)
        if locations is not None:
            version_q = version_q.filter(BomSnapshot.location.in_(locations))
        elif location is not None:
            version_q = version_q.filter(BomSnapshot.location == location)
        if vehicle_model is not None:
            version_q = version_q.filter(BomSnapshot.vehicle_model == vehicle_model)
        bom_versions = [
            row[0] for row in version_q.order_by(BomSnapshot.bom_version.desc()).all() if row[0]
        ]

        return {
            "locations": distinct_locations,
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

    def list_as_of_trees(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        as_of_year: int,
        as_of_month: int,
    ) -> list[BomNode]:
        """L0 命中 as_of 的树（含子树）。按月命中以树根为准。"""
        all_nodes = self.list_by_location_vehicle(
            db, location=location, vehicle_model=vehicle_model
        )
        return nodes_in_as_of_trees(all_nodes, as_of_year=as_of_year, as_of_month=as_of_month)

    def list_year_overlap_trees_for_snapshot(
        self,
        db: Session,
        *,
        snapshot_id: int,
        year: int,
    ) -> list[BomNode]:
        """该 snapshot 内：树根年交集命中的整棵树。禁止用 L1/L2 本行期。"""
        all_nodes = self.list_by_snapshot(db, snapshot_id)
        return nodes_in_year_overlap_trees(all_nodes, year=year)

    def count_by_snapshot_and_level(self, db: Session, snapshot_id: int, level: int) -> int:
        return (
            db.query(BomNode)
            .filter(BomNode.snapshot_id == snapshot_id, BomNode.level == level)
            .count()
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

    def delete_by_snapshot(self, db: Session, snapshot_id: int) -> int:
        count = (
            db.query(BomNode)
            .filter(BomNode.snapshot_id == snapshot_id)
            .delete(synchronize_session=False)
        )
        db.flush()
        return count

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
