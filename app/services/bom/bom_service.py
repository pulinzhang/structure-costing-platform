"""BOM Service - 业务逻辑"""

from typing import Any
import logging
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.common.audit import audit_create
from app.common.bom.manufacturing_category import resolve_manufacturing_category
from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.schemas.dto.bom_dto import BomNodeCreate, BomSnapshotCreate, BomSnapshotQuery
from app.schemas.vo.bom_vo import (
    BomCascadeFilterOptionsVO,
    BomCascadeFilterQuery,
    BomNodeTreeVO,
    BomNodeVO,
    BomSnapshotVO,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.bom")

_ALLOWED_STAGES = {"initial", "mass"}
_ALLOWED_STATUSES = {"draft", "active", "archived"}
# 冲焊件 BOM 角色：无电子/电气品类
_ALLOWED_ROLES = {"supply", "structure", "make", "buy", "consumable"}


class BomService:
    """BOM 清单与树节点业务（冲焊件供应商域）"""

    def __init__(self) -> None:
        self.snapshot_repo = BomSnapshotRepository()
        self.node_repo = BomNodeRepository()

    @staticmethod
    def _to_node_vo(row: Any, *, has_children: bool = False) -> BomNodeVO:
        vo = BomNodeVO.model_validate(row)
        vo.manufacturing_category = resolve_manufacturing_category(
            node_role=vo.node_role,
            is_supply_unit=bool(vo.is_supply_unit),
            has_children=has_children,
            part_name=vo.part_name,
            material=vo.material,
            part_number=vo.part_number,
            thickness_mm=vo.thickness_mm,
            qty_unit=vo.qty_unit,
        )
        return vo

    def list_nodes_flat(self, db: Session, snapshot_id: int) -> list[BomNodeVO] | None:
        if not self.snapshot_repo.get_by_id(db, snapshot_id):
            return None
        rows = self.node_repo.list_by_snapshot(db, snapshot_id)
        parent_ids_with_children = {r.parent_id for r in rows if r.parent_id is not None}
        return [
            self._to_node_vo(r, has_children=r.id in parent_ids_with_children)
            for r in rows
        ]

    def paginate_snapshots(
        self, db: Session, query: BomSnapshotQuery
    ) -> tuple[list[BomSnapshotVO], int, dict[str, Any]]:
        skip = (query.page - 1) * query.size
        rows, total = self.snapshot_repo.paginate(
            db,
            location=query.location,
            vehicle_model=query.vehicle_model,
            status=query.status,
            skip=skip,
            limit=query.size,
        )
        items: list[BomSnapshotVO] = []
        for row in rows:
            vo = BomSnapshotVO.model_validate(row)
            vo.node_count = self.snapshot_repo.count_nodes(db, row.id)
            items.append(vo)

        filters = {
            "locations": self.snapshot_repo.list_locations(db),
            "vehicle_models": self.snapshot_repo.list_vehicle_models(db),
        }
        return items, total, filters

    def get_cascade_filter_options(
        self,
        db: Session,
        query: BomCascadeFilterQuery,
    ) -> BomCascadeFilterOptionsVO:
        raw = self.snapshot_repo.get_cascade_filter_options(
            db,
            location=query.location,
            vehicle_model=query.vehicle_model,
            status=query.status,
        )
        return BomCascadeFilterOptionsVO.model_validate(raw)

    def get_snapshot(self, db: Session, snapshot_id: int) -> BomSnapshotVO | None:
        row = self.snapshot_repo.get_by_id(db, snapshot_id)
        if not row:
            return None
        vo = BomSnapshotVO.model_validate(row)
        vo.node_count = self.snapshot_repo.count_nodes(db, row.id)
        return vo

    def create_snapshot(
        self,
        db: Session,
        data: BomSnapshotCreate,
        current_user: UserVO,
    ) -> tuple[BomSnapshotVO | None, str | None]:
        if data.stage not in _ALLOWED_STAGES:
            return None, f"stage 无效，允许: {', '.join(sorted(_ALLOWED_STAGES))}"
        if data.status not in _ALLOWED_STATUSES:
            return None, f"status 无效，允许: {', '.join(sorted(_ALLOWED_STATUSES))}"

        existing = self.snapshot_repo.get_by_unique_key(
            db, data.location, data.vehicle_model, data.bom_version
        )
        if existing:
            return None, (
                f"BOM 已存在: {data.location} / {data.vehicle_model} / {data.bom_version}"
            )

        try:
            payload = {**data.model_dump(), **audit_create(current_user)}
            row = self.snapshot_repo.create(db, payload)
            vo = BomSnapshotVO.model_validate(row)
            vo.node_count = 0
            return vo, None
        except IntegrityError:
            db.rollback()
            return None, "BOM 唯一键冲突（基地+车型+版本）"
        except Exception as exc:
            db.rollback()
            logger.error("创建 BOM snapshot 失败: %s", exc)
            return None, str(exc)

    def delete_snapshot(self, db: Session, snapshot_id: int) -> str | None:
        row = self.snapshot_repo.get_by_id(db, snapshot_id)
        if not row:
            return "BOM 清单不存在"
        try:
            self.snapshot_repo.delete(db, row)
            return None
        except Exception as exc:
            db.rollback()
            logger.error("删除 BOM snapshot 失败: %s", exc)
            return str(exc)

    def list_nodes_tree(self, db: Session, snapshot_id: int) -> list[BomNodeTreeVO] | None:
        flat = self.list_nodes_flat(db, snapshot_id)
        if flat is None:
            return None
        return self._build_tree(flat)

    def create_node(
        self,
        db: Session,
        snapshot_id: int,
        data: BomNodeCreate,
        current_user: UserVO,
    ) -> tuple[BomNodeVO | None, str | None]:
        snapshot = self.snapshot_repo.get_by_id(db, snapshot_id)
        if not snapshot:
            return None, "BOM 清单不存在"
        if data.node_role not in _ALLOWED_ROLES:
            return None, f"node_role 无效，允许: {', '.join(sorted(_ALLOWED_ROLES))}"

        if data.parent_id is None:
            if data.level != 0:
                return None, "无父节点时 level 必须为 0"
        else:
            parent = self.node_repo.get_by_id(db, data.parent_id)
            if not parent or parent.snapshot_id != snapshot_id:
                return None, "父节点不存在或不属于该 BOM"
            if data.level != parent.level + 1:
                return None, f"子节点 level 应为 {parent.level + 1}"

        try:
            payload = {
                **data.model_dump(),
                "snapshot_id": snapshot_id,
                **audit_create(current_user),
            }
            row = self.node_repo.create(db, payload)
            return self._to_node_vo(row), None
        except Exception as exc:
            db.rollback()
            logger.error("创建 BOM node 失败: %s", exc)
            return None, str(exc)

    def delete_node(self, db: Session, node_id: int) -> str | None:
        row = self.node_repo.get_by_id(db, node_id)
        if not row:
            return "节点不存在"
        try:
            self.node_repo.delete(db, row)
            return None
        except Exception as exc:
            db.rollback()
            logger.error("删除 BOM node 失败: %s", exc)
            return str(exc)

    @staticmethod
    def _build_tree(flat: list[BomNodeVO]) -> list[BomNodeTreeVO]:
        by_id: dict[int, BomNodeTreeVO] = {}
        roots: list[BomNodeTreeVO] = []
        for item in flat:
            node = BomNodeTreeVO(**item.model_dump(), children=[])
            by_id[node.id] = node
        for item in flat:
            node = by_id[item.id]
            if item.parent_id and item.parent_id in by_id:
                by_id[item.parent_id].children.append(node)
            else:
                roots.append(node)
        return roots
