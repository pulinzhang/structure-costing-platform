"""BOM Service - 业务逻辑"""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.exceptions.base import BusinessException, NotFoundException
from app.common.bom.manufacturing_category import resolve_manufacturing_category
from app.models.bom import BomNode
from app.repositories.bom.bom_repository import (
    BomNodeRepository,
    BomSnapshotListFilters,
    BomSnapshotRepository,
)
from app.schemas.dto.bom_dto import (
    BomNodeCreate,
    BomNodeWrite,
    BomSnapshotCreate,
    BomSnapshotQuery,
    BomSnapshotWrite,
)
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
    def _to_node_vo(row: BomNode, *, has_children: bool = False) -> BomNodeVO:
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

    def list_nodes_flat(self, db: Session, snapshot_id: int) -> list[BomNodeVO]:
        if not self.snapshot_repo.get_by_id(db, snapshot_id):
            raise NotFoundException("BOM 清单不存在")
        rows = self.node_repo.list_by_snapshot(db, snapshot_id)
        parent_ids_with_children = {r.parent_id for r in rows if r.parent_id is not None}
        return [
            self._to_node_vo(r, has_children=r.id in parent_ids_with_children)
            for r in rows
        ]

    def paginate_snapshots(
        self, db: Session, query: BomSnapshotQuery
    ) -> tuple[list[BomSnapshotVO], int, BomSnapshotListFilters]:
        skip = (query.page - 1) * query.size
        rows, total = self.snapshot_repo.paginate(
            db,
            location=query.location,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            status=query.status,
            skip=skip,
            limit=query.size,
        )
        items: list[BomSnapshotVO] = []
        for row in rows:
            vo = BomSnapshotVO.model_validate(row)
            vo.node_count = self.snapshot_repo.count_nodes(db, row.id)
            items.append(vo)

        summary_raw = self.snapshot_repo.summarize(
            db,
            location=query.location,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            status=query.status,
        )
        filters: BomSnapshotListFilters = {
            "locations": self.snapshot_repo.list_locations(db),
            "vehicle_models": self.snapshot_repo.list_vehicle_models(db),
            "bom_versions": self.snapshot_repo.list_bom_versions(db),
            "statuses": self.snapshot_repo.list_statuses(db),
            "summary": summary_raw,
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

    def get_snapshot(self, db: Session, snapshot_id: int) -> BomSnapshotVO:
        row = self.snapshot_repo.get_by_id(db, snapshot_id)
        if not row:
            raise NotFoundException("BOM 清单不存在")
        vo = BomSnapshotVO.model_validate(row)
        vo.node_count = self.snapshot_repo.count_nodes(db, row.id)
        return vo

    def create_snapshot(
        self,
        db: Session,
        data: BomSnapshotCreate,
        current_user: UserVO,
    ) -> BomSnapshotVO:
        if data.stage not in _ALLOWED_STAGES:
            raise BusinessException(
                f"stage 无效，允许: {', '.join(sorted(_ALLOWED_STAGES))}"
            )
        if data.status not in _ALLOWED_STATUSES:
            raise BusinessException(
                f"status 无效，允许: {', '.join(sorted(_ALLOWED_STATUSES))}"
            )

        existing = self.snapshot_repo.get_by_unique_key(
            db, data.location, data.vehicle_model, data.bom_version
        )
        if existing:
            raise BusinessException(
                f"BOM 已存在: {data.location} / {data.vehicle_model} / {data.bom_version}"
            )

        try:
            audit = audit_create(current_user)
            row = self.snapshot_repo.create(
                db,
                BomSnapshotWrite(
                    location=data.location,
                    vehicle_model=data.vehicle_model,
                    bom_version=data.bom_version,
                    source_filename=data.source_filename,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                    product_category=data.product_category,
                    customer_name=data.customer_name,
                    stage=data.stage,
                    doc_no=data.doc_no,
                    prepare_dept=data.prepare_dept,
                    doc_date=data.doc_date,
                    revision_date=data.revision_date,
                    title=data.title,
                    source_file_hash=data.source_file_hash,
                    status=data.status,
                    remark=data.remark,
                ),
            )
            db.commit()
            db.refresh(row)
            vo = BomSnapshotVO.model_validate(row)
            vo.node_count = 0
            return vo
        except IntegrityError:
            db.rollback()
            raise BusinessException("BOM 唯一键冲突（基地+车型+版本）") from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建 BOM snapshot 失败")
            raise

    def delete_snapshot(self, db: Session, snapshot_id: int) -> None:
        row = self.snapshot_repo.get_by_id(db, snapshot_id)
        if not row:
            raise NotFoundException("BOM 清单不存在")
        try:
            self.snapshot_repo.delete(db, row)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("删除 BOM snapshot 失败")
            raise

    def list_nodes_tree(self, db: Session, snapshot_id: int) -> list[BomNodeTreeVO]:
        return self._build_tree(self.list_nodes_flat(db, snapshot_id))

    def create_node(
        self,
        db: Session,
        snapshot_id: int,
        data: BomNodeCreate,
        current_user: UserVO,
    ) -> BomNodeVO:
        snapshot = self.snapshot_repo.get_by_id(db, snapshot_id)
        if not snapshot:
            raise NotFoundException("BOM 清单不存在")
        if data.node_role not in _ALLOWED_ROLES:
            raise BusinessException(
                f"node_role 无效，允许: {', '.join(sorted(_ALLOWED_ROLES))}"
            )

        if data.parent_id is None:
            if data.level != 0:
                raise BusinessException("无父节点时 level 必须为 0")
        else:
            parent = self.node_repo.get_by_id(db, data.parent_id)
            if not parent or parent.snapshot_id != snapshot_id:
                raise NotFoundException("父节点不存在或不属于该 BOM")
            if data.level != parent.level + 1:
                raise BusinessException(f"子节点 level 应为 {parent.level + 1}")

        try:
            audit = audit_create(current_user)
            row = self.node_repo.create(
                db,
                BomNodeWrite(
                    snapshot_id=snapshot_id,
                    level=data.level,
                    part_number=data.part_number,
                    node_role=data.node_role,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                    parent_id=data.parent_id,
                    sort_no=data.sort_no,
                    seq_no=data.seq_no,
                    internal_number=data.internal_number,
                    part_name=data.part_name,
                    qty=data.qty,
                    qty_unit=data.qty_unit,
                    qty_text=data.qty_text,
                    is_supply_unit=data.is_supply_unit,
                    material=data.material,
                    thickness_mm=data.thickness_mm,
                    thickness_text=data.thickness_text,
                    material_mill=data.material_mill,
                    part_weight=data.part_weight,
                    gauge_developed=data.gauge_developed,
                    weld_info=data.weld_info,
                    remark=data.remark,
                    sketch_url=data.sketch_url,
                ),
            )
            db.commit()
            db.refresh(row)
            return self._to_node_vo(row)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建 BOM node 失败")
            raise

    def delete_node(self, db: Session, node_id: int) -> None:
        row = self.node_repo.get_by_id(db, node_id)
        if not row:
            raise NotFoundException("节点不存在")
        try:
            self.node_repo.delete(db, row)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("删除 BOM node 失败")
            raise

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
