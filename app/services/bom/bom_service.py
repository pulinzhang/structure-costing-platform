"""BOM Service - 业务逻辑"""

import logging
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.common.bom.manufacturing_category import resolve_manufacturing_category
from app.common.period import is_in_period, resolve_as_of_month, validate_period
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom import BomNode
from app.parsers.bom.bom_parser import BomParsedNode
from app.repositories.bom.bom_repository import (
    BomNodeRepository,
    BomSnapshotListFilters,
    BomSnapshotRepository,
)
from app.repositories.bom.period_trees import nodes_in_as_of_trees
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.dto.bom_dto import (
    BomCascadeFilterQuery,
    BomNodeCreate,
    BomNodeWrite,
    BomSnapshotCreate,
    BomSnapshotQuery,
    BomSnapshotWrite,
)
from app.schemas.vo.bom_vo import (
    BomCascadeFilterOptionsVO,
    BomNodeTreeVO,
    BomNodeVO,
    BomSnapshotVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.change_tree_plant import (
    BomChangePlantResult,
    BomChangePlantSpec,
)
from app.services.bom.change_tree_plant import (
    plant_change_tree as plant_change_tree_fn,
)
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.vehicle_model import VehicleModelService

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
        self._procurement_repo = BomProcurementObjectRepository()
        self._breakdown_repo = BomWeldingProcessBreakdownRepository()

    def assert_bom_scope_unused(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        action: str,
    ) -> None:
        """有直接下游（采购对象、焊接拆解）则禁止覆盖导入或删除材料清单/节点。"""
        found: list[str] = []
        if self._procurement_repo.get_list_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        ):
            found.append("采购对象清单")
        if self._breakdown_repo.exists_by_bom_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        ):
            found.append("焊接工艺拆解")
        if not found:
            return
        labels = "、".join(found)
        raise BusinessException(
            f"该版本已有{labels}，不能{action}材料清单。"
            "请改用新的 BOM 版本导入，或先删除上述下游后再操作。",
            code=409,
        )

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
            rows = _filter_hit_subtrees(rows, as_of_year, as_of_month)
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

    def paginate_snapshots(
        self, db: Session, query: BomSnapshotQuery
    ) -> tuple[list[BomSnapshotVO], int, BomSnapshotListFilters]:
        skip = (query.page - 1) * query.size
        location_service = LocationService()
        locations: list[str] | None = None
        if query.location:
            locations = location_service.expand_for_query(db, query.location)
            if not locations:
                empty_filters: BomSnapshotListFilters = {
                    "locations": location_service.list_registered(db),
                    "vehicle_models": VehicleModelService().list_filter_codes(db, query.location),
                    "bom_versions": self.snapshot_repo.list_bom_versions(db),
                    "statuses": self.snapshot_repo.list_statuses(db),
                    "summary": {
                        "total_count": 0,
                        "active_count": 0,
                        "draft_count": 0,
                        "archived_count": 0,
                        "total_node_count": 0,
                    },
                }
                return [], 0, empty_filters
        rows, total = self.snapshot_repo.paginate(
            db,
            locations=locations,
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
            locations=locations,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            status=query.status,
        )
        filters: BomSnapshotListFilters = {
            "locations": location_service.list_registered(db),
            "vehicle_models": VehicleModelService().list_filter_codes(db, query.location),
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
        location_service = LocationService()
        location_raw = (query.location or "").strip() or None
        locations: list[str] | None = None
        if location_raw:
            locations = location_service.expand_for_query(db, location_raw)
            if not locations:
                return BomCascadeFilterOptionsVO(
                    locations=location_service.list_enabled(db),
                    vehicle_models=[],
                    bom_versions=[],
                )
        raw = self.snapshot_repo.get_cascade_filter_options(
            db,
            locations=locations,
            vehicle_model=query.vehicle_model,
            status=query.status,
        )
        vehicle_svc = VehicleModelService()
        if location_raw and query.year is not None:
            if query.month is not None:
                vehicle_models = vehicle_svc.list_introducible(
                    db, location_raw, query.year, query.month
                )
            else:
                vehicle_models = vehicle_svc.list_overlaps_year(db, location_raw, query.year)
        else:
            vehicle_models = vehicle_svc.list_filter_codes(db, location_raw)
        return BomCascadeFilterOptionsVO(
            locations=location_service.list_enabled(db),
            vehicle_models=vehicle_models,
            bom_versions=list(raw["bom_versions"]),
        )

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
            raise BusinessException(f"stage 无效，允许: {', '.join(sorted(_ALLOWED_STAGES))}")
        if data.status not in _ALLOWED_STATUSES:
            raise BusinessException(f"status 无效，允许: {', '.join(sorted(_ALLOWED_STATUSES))}")

        location = LocationService().require_enabled(db, data.location)
        existing = self.snapshot_repo.get_by_unique_key(
            db, location, data.vehicle_model, data.bom_version
        )
        if existing:
            raise BusinessException(
                f"BOM 已存在: {location} / {data.vehicle_model} / {data.bom_version}"
            )

        try:
            audit = audit_create(current_user)
            row = self.snapshot_repo.create(
                db,
                BomSnapshotWrite(
                    location=location,
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
        self.assert_bom_scope_unused(
            db,
            location=row.location,
            vehicle_model=row.vehicle_model,
            bom_version=row.bom_version,
            action="删除",
        )
        try:
            self.snapshot_repo.delete(db, row)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("删除 BOM snapshot 失败")
            raise

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
        self.assert_bom_scope_unused(
            db,
            location=snapshot.location,
            vehicle_model=snapshot.vehicle_model,
            bom_version=snapshot.bom_version,
            action="删除",
        )
        try:
            self.node_repo.delete(db, row)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("删除 BOM node 失败")
            raise

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
        nodes = self.node_repo.list_as_of_trees(
            db,
            location=location,
            vehicle_model=vehicle_model,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )
        by_id = {node.id: node for node in nodes}
        for node in nodes:
            if (node.part_number or "").strip() != target:
                continue
            root = node
            while root.parent_id is not None:
                parent = by_id.get(root.parent_id)
                if parent is None:
                    break
                root = parent
            if root.id not in excluded:
                return True
        return False

    def get_node_row(self, db: Session, node_id: int) -> BomNode | None:
        """工程变更门面：按 id 取节点行（可空）。"""
        return self.node_repo.get_by_id(db, node_id)

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
        """工程变更门面：合册种新树。只 flush。"""
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


def _filter_hit_subtrees(rows: list[BomNode], as_of_year: int, as_of_month: int) -> list[BomNode]:
    """L0 月命中再收子树；口径见 repositories.bom.period_trees。"""
    return nodes_in_as_of_trees(rows, as_of_year=as_of_year, as_of_month=as_of_month)


def _descendant_ids(rows: list[BomNode], roots: set[int]) -> set[int]:
    children_of: dict[int, list[int]] = {}
    for row in rows:
        if row.parent_id is None:
            continue
        children_of.setdefault(row.parent_id, []).append(row.id)
    keep = set(roots)
    stack = list(roots)
    while stack:
        current = stack.pop()
        for child_id in children_of.get(current, []):
            if child_id in keep:
                continue
            keep.add(child_id)
            stack.append(child_id)
    return keep


def collect_subtree(rows: list[BomNode], root_id: int) -> list[BomNode]:
    """含 root 的整棵子树（同 snapshot 节点列表上按 parent_id 展开）。"""
    keep = _descendant_ids(rows, {root_id})
    return [row for row in rows if row.id in keep]
