"""BOM 树节点：清单内列表与手工增删。"""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.bom.manufacturing_category import resolve_manufacturing_category
from app.common.period import resolve_as_of_month
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom import BomNode
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.repositories.bom.period_trees import nodes_in_as_of_trees
from app.schemas.dto.bom_dto import BomNodeCreate, BomNodeWrite
from app.schemas.vo.bom_vo import BomNodeTreeVO, BomNodeVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.trees import descendant_ids
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.services.settings.foreign_key.service import STILL_REFERENCED, ensure_deletable

logger = logging.getLogger("service.bom.node")

_ALLOWED_ROLES = {"supply", "structure", "make", "buy", "consumable"}


class BomNodeService:
    """材料清单树节点（冲焊件）。"""

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

    def list_nodes_flat(
        self,
        db: Session,
        snapshot_id: int,
        *,
        year: int | None = None,
        month: int | None = None,
        include_expired: bool = False,
    ) -> list[BomNodeVO]:
        if not self.snapshot_repo.get_by_id(db, snapshot_id):
            raise NotFoundException("BOM 清单不存在")
        rows = self.node_repo.list_by_snapshot(db, snapshot_id)
        if not include_expired:
            as_of_year, as_of_month = resolve_as_of_month(year, month)
            rows = nodes_in_as_of_trees(rows, as_of_year=as_of_year, as_of_month=as_of_month)
        parent_ids_with_children = {r.parent_id for r in rows if r.parent_id is not None}
        return [self._to_node_vo(r, has_children=r.id in parent_ids_with_children) for r in rows]

    def list_nodes_tree(
        self,
        db: Session,
        snapshot_id: int,
        *,
        year: int | None = None,
        month: int | None = None,
        include_expired: bool = False,
    ) -> list[BomNodeTreeVO]:
        return self._build_tree(
            self.list_nodes_flat(
                db,
                snapshot_id,
                year=year,
                month=month,
                include_expired=include_expired,
            )
        )

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
            raise BusinessException(f"node_role 无效，允许: {', '.join(sorted(_ALLOWED_ROLES))}")

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
            if data.parent_id is None:
                effective_year, effective_month, expiry_year, expiry_month = (
                    VehicleModelService().project_sop_period(db, snapshot.location, snapshot.vehicle_model)
                )
            else:
                parent = self.node_repo.get_by_id(db, data.parent_id)
                if parent is None:
                    raise NotFoundException("父节点不存在或不属于该 BOM")
                effective_year = parent.effective_year
                effective_month = parent.effective_month
                expiry_year = parent.expiry_year
                expiry_month = parent.expiry_month
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
                    location=snapshot.location,
                    vehicle_model=snapshot.vehicle_model,
                    bom_version=snapshot.bom_version,
                    effective_year=effective_year,
                    effective_month=effective_month,
                    expiry_year=expiry_year,
                    expiry_month=expiry_month,
                ),
            )
            db.commit()
            db.refresh(row)
            return self._to_node_vo(row)
        except IntegrityError:
            db.rollback()
            raise BusinessException("同一清单下总成零件号已存在") from None
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
        snapshot = self.snapshot_repo.get_by_id(db, row.snapshot_id)
        if not snapshot:
            raise NotFoundException("BOM 清单不存在")
        rows = self.node_repo.list_by_snapshot(db, snapshot.id)
        node_ids = sorted(descendant_ids(rows, {row.id}))
        location = snapshot.location
        vehicle_model = snapshot.vehicle_model
        try:
            ensure_deletable(
                db,
                "bom_nodes",
                [{"id": node_id} for node_id in node_ids],
                subject=f"材料清单节点「{location} {vehicle_model}」",
            )
            self.node_repo.delete(db, row)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException(STILL_REFERENCED) from None
        except BusinessException:
            db.rollback()
            raise
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
