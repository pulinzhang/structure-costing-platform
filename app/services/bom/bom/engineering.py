"""工程变更树：找 L0、失效、种树、回滚删树。"""

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.common.audit import audit_update
from app.common.period import is_in_period, validate_period
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom import BomNode
from app.parsers.bom.bom_parser import BomParsedNode
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.repositories.bom.period_trees import tree_root_of
from app.schemas.dto.bom_dto import BomNodeWrite
from app.schemas.vo.bom_vo import BomSnapshotVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.change_tree_plant.plant import plant_change_tree as plant_change_tree_fn
from app.services.bom.bom.change_tree_plant.types import BomChangePlantResult, BomChangePlantSpec
from app.services.bom.bom.period import BomPeriodService
from app.services.bom.bom.snapshot import BomSnapshotService
from app.services.bom.bom.trees import collect_subtree
from app.services.settings.schema_comment.service import ensure_deletable

__all__ = [
    "BomChangePlantResult",
    "BomChangePlantSpec",
    "BomEngineeringService",
]


class BomEngineeringService:
    """工程变更对材料清单树的读写。"""

    def __init__(self) -> None:
        self.snapshot_repo = BomSnapshotRepository()
        self.node_repo = BomNodeRepository()

    def get_snapshot(self, db: Session, snapshot_id: int) -> BomSnapshotVO:
        return BomSnapshotService().get_snapshot(db, snapshot_id)

    def find_active_l0_by_part_number(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        part_number: str,
        as_of_year: int,
        as_of_month: int,
    ) -> BomNode | None:
        """工程变更：在基地+项目全部 snapshot 中找当月命中的 L0。"""
        snapshots = self.snapshot_repo.list_by_location_model(db, location, vehicle_model)
        for snapshot in snapshots:
            root = self.node_repo.get_l0_by_part_number(db, snapshot.id, part_number)
            if root is None:
                continue
            if is_in_period(
                effective_year=root.effective_year,
                effective_month=root.effective_month,
                expiry_year=root.expiry_year,
                expiry_month=root.expiry_month,
                as_of_year=as_of_year,
                as_of_month=as_of_month,
            ):
                return root
        return None

    def find_l0_by_part_number(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        part_number: str,
    ) -> BomNode | None:
        """工程变更：任意状态 L0（用于变更后总成已存在校验）。"""
        snapshots = self.snapshot_repo.list_by_location_model(db, location, vehicle_model)
        for snapshot in snapshots:
            root = self.node_repo.get_l0_by_part_number(db, snapshot.id, part_number)
            if root is not None:
                return root
        return None

    def expire_l0_tree(
        self,
        db: Session,
        *,
        root_id: int,
        expiry_year: int,
        expiry_month: int,
        current_user: UserVO,
    ) -> BomNode:
        """工程变更门面：子树写失效月；只 flush，由调用方 commit。"""
        row = self.node_repo.get_by_id(db, root_id)
        if not row:
            raise NotFoundException("节点不存在")
        if row.level != 0:
            raise BusinessException("只能改总成（L0）生失效")
        validate_period(
            row.effective_year,
            row.effective_month,
            expiry_year,
            expiry_month,
        )
        audit = audit_update(current_user)
        subtree = collect_subtree(self.node_repo.list_by_snapshot(db, row.snapshot_id), row.id)
        for node in subtree:
            node.expiry_year = expiry_year
            node.expiry_month = expiry_month
            node.updated_by = audit["updated_by"]
        db.flush()
        return row

    def clear_l0_expiry(
        self,
        db: Session,
        *,
        root_id: int,
        current_user: UserVO,
    ) -> BomNode:
        """工程变更回滚：去掉 L0 子树失效月。"""
        row = self.node_repo.get_by_id(db, root_id)
        if not row:
            raise NotFoundException("节点不存在")
        if row.level != 0:
            raise BusinessException("只能改总成（L0）生失效")
        audit = audit_update(current_user)
        subtree = collect_subtree(self.node_repo.list_by_snapshot(db, row.snapshot_id), row.id)
        for node in subtree:
            node.expiry_year = None
            node.expiry_month = None
            node.updated_by = audit["updated_by"]
        db.flush()
        return row

    def delete_engineering_change_tree(
        self,
        db: Session,
        *,
        root_id: int,
        current_user: UserVO,
    ) -> None:
        """工程变更回滚：删新树（子孙先删）。只 flush。"""
        _ = current_user
        row = self.node_repo.get_by_id(db, root_id)
        if not row:
            return
        if row.level != 0:
            raise BusinessException("只能删除总成（L0）树")
        subtree = collect_subtree(self.node_repo.list_by_snapshot(db, row.snapshot_id), row.id)
        ensure_deletable(
            db,
            "bom_nodes",
            [{"id": node.id} for node in subtree],
            subject="这些材料清单节点",
        )
        self.node_repo.delete_descendants(db, row.snapshot_id, row.id)
        self.node_repo.delete(db, row)
        db.flush()

    def list_subtree_nodes(self, db: Session, *, root_id: int) -> list[BomNode]:
        """工程变更门面：返回含根的子树节点（只读）。"""
        row = self.node_repo.get_by_id(db, root_id)
        if not row:
            raise NotFoundException("节点不存在")
        return collect_subtree(self.node_repo.list_by_snapshot(db, row.snapshot_id), row.id)

    def part_number_used_on_other_active_l0(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        part_number: str,
        as_of_year: int,
        as_of_month: int,
        exclude_l0_ids: set[int],
    ) -> bool:
        """工程变更：零件号是否仍挂在排除树以外的当月有效总成上。"""
        target = (part_number or "").strip()
        if not target:
            return False
        excluded = set(exclude_l0_ids)
        nodes = BomPeriodService().list_as_of_trees(
            db,
            location=location,
            vehicle_model=vehicle_model,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )
        by_id = {int(node.id): node for node in nodes}
        for node in nodes:
            if (node.part_number or "").strip() != target:
                continue
            root = tree_root_of(node, by_id)
            if int(root.id) not in excluded:
                return True
        return False

    def get_node_row(self, db: Session, node_id: int) -> BomNode | None:
        """工程变更门面：按 id 取节点行（可空）。"""
        return self.node_repo.get_by_id(db, node_id)

    def list_node_rows_by_ids(self, db: Session, node_ids: list[int]) -> list[BomNode]:
        """工程变更门面：按 id 批量取节点行。"""
        return self.node_repo.list_by_ids(db, node_ids)

    def create_engineering_change_node(self, db: Session, data: BomNodeWrite) -> BomNode:
        """工程变更门面：插节点（不走 SOP 期校验）。只 flush。"""
        return self.node_repo.create(db, data)

    def plant_change_tree(
        self,
        db: Session,
        *,
        snapshot_id: int,
        location: str,
        vehicle_model: str,
        before_l0_id: int,
        seq_no: int | None,
        spec: BomChangePlantSpec,
        parsed_nodes: list[BomParsedNode],
        extra_specs: Sequence[BomChangePlantSpec] = (),
        effective_year: int,
        effective_month: int,
        expiry_year: int | None,
        expiry_month: int | None,
        current_user: UserVO,
        node_bom_version: str | None = None,
    ) -> BomChangePlantResult:
        """工程变更门面：工程变更种新树。只 flush。"""
        return plant_change_tree_fn(
            self,
            db,
            snapshot_id=snapshot_id,
            location=location,
            vehicle_model=vehicle_model,
            before_l0_id=before_l0_id,
            seq_no=seq_no,
            spec=spec,
            parsed_nodes=parsed_nodes,
            extra_specs=extra_specs,
            effective_year=effective_year,
            effective_month=effective_month,
            expiry_year=expiry_year,
            expiry_month=expiry_month,
            current_user=current_user,
            node_bom_version=node_bom_version,
        )
