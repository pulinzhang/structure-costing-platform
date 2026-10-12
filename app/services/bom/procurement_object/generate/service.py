"""采购对象列表 — 从材料清单树生成。

列入规则在 classify：退化仅 L0（无子件，或全部 L1 无内部号）。L1 有内部号才列入采购对象。

找 snapshot（§13 干净库）：写路径 require_enabled + normalize_vehicle_model + 精确匹配；
prep 同 normalize、不强制 require_enabled。禁止在本文件 expand 基地别名。

投产版本（snapshot 头字）整包删头重写。变更版本（只在树根上）只换这些树的行，清单头留下。
"""

from __future__ import annotations

import logging
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AuditCreateFields, audit_create, display_name
from app.common.engineering_change_gates import (
    EC_GATE_FULL_GENERATE,
    PeriodRoot,
    snapshot_blocks_full_generate,
)
from app.common.timezone import now
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom.node import BomNode, BomSnapshot
from app.models.bom.procurement_object import BomProcurementObjectList
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectGenerateDTO,
    BomProcurementObjectListWrite,
    BomProcurementObjectPrepQuery,
)
from app.schemas.vo.bom_procurement_object_vo import (
    BomProcurementObjectGenerateResultVO,
    BomProcurementObjectListVO,
    BomProcurementObjectPrepStatsVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.trees import descendant_ids
from app.services.bom.procurement_object.classify import (
    SECTION_OBJECT,
    ClassifyResult,
    classify_nodes,
)
from app.services.bom.procurement_object.generate.log import (
    BomProcurementObjectGenerateLogService,
)
from app.services.bom.procurement_object.row_write import ConfirmByNode, build_object_row_write
from app.services.bom.procurement_object.snapshot_scope import lookup_snapshot
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.vehicle_model.service import VehicleModelService

logger = logging.getLogger("service.bom.procurement_object.generate")

_CHANGE_VERSION_NEEDS_SOP = "请先按投产版本生成采购对象，再生成这个变更版本"
_APPROVED_BLOCKS = "该范围已有已审核采购对象，须先批量反审核后再生成"
_APPROVED_BLOCKS_CHANGE = "该变更版本已有已审核采购对象，禁止覆盖生成；请先批量反审核"


class _Written(NamedTuple):
    header: BomProcurementObjectList
    classified: ClassifyResult
    node_count: int
    confirm_by_node: ConfirmByNode


class BomProcurementObjectGenerateService:
    def __init__(self) -> None:
        self.node_repo = BomNodeRepository()
        self.repository = BomProcurementObjectRepository()
        self.log_service = BomProcurementObjectGenerateLogService()

    def prep_stats(
        self, db: Session, query: BomProcurementObjectPrepQuery
    ) -> BomProcurementObjectPrepStatsVO:
        location = (query.location or "").strip()
        vehicle_model = normalize_vehicle_model(query.vehicle_model)
        bom_version = (query.bom_version or "").strip()
        if not location or not vehicle_model or not bom_version:
            return BomProcurementObjectPrepStatsVO(
                message="请选定基地 / 项目 / 版本",
            )
        snapshot = lookup_snapshot(
            db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
        )
        if snapshot is not None:
            return self._prep_snapshot(db, snapshot)
        loaded = self._load_change_version_nodes(
            db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
        )
        if loaded is None:
            return BomProcurementObjectPrepStatsVO(
                message="未找到对应材料清单，请先上传 BOM",
            )
        change_snapshot, nodes = loaded
        return self._prep_change_version(db, change_snapshot, nodes)

    def generate(
        self,
        db: Session,
        dto: BomProcurementObjectGenerateDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectGenerateResultVO:
        started_at = now()
        location = LocationService().require_enabled(db, dto.location)
        vehicle_model = normalize_vehicle_model(dto.vehicle_model)
        if not vehicle_model:
            raise BusinessException("项目代号无效")
        bom_version = dto.bom_version.strip()
        snapshot_id: int | None = None
        node_count = 0
        object_count = 0
        other_leaf_count = 0
        anomaly_count = 0
        qa_passed = False
        audit = audit_create(current_user)

        try:
            snapshot = lookup_snapshot(
                db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
            )
            if snapshot is not None:
                written = self._replace_snapshot(
                    db,
                    snapshot=snapshot,
                    audit=audit,
                    operator=display_name(current_user),
                )
            else:
                written = self._replace_change_trees(
                    db,
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                )
            classified = written.classified
            snapshot_id = written.header.snapshot_id
            node_count = written.node_count
            object_count = _listed_object_count(classified)
            other_leaf_count = classified.counts.other_leaf_count
            anomaly_count = classified.counts.anomaly_count
            qa_passed = classified.qa_passed
            payloads = [
                build_object_row_write(
                    db,
                    classified_row,
                    list_id=written.header.id,
                    confirm_by_node=written.confirm_by_node,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                )
                for classified_row in classified.rows
            ]
            self.repository.bulk_create_objects(db, payloads)
            self.log_service.write_success(
                db,
                current_user=current_user,
                started_at=started_at,
                finished_at=now(),
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                snapshot_id=snapshot_id,
                node_count=node_count,
                object_count=object_count,
                other_leaf_count=other_leaf_count,
                anomaly_count=anomaly_count,
                qa_passed=qa_passed,
                object_l0_degenerate_count=classified.counts.object_l0_degenerate_count,
                object_l0_special_process_count=classified.counts.object_l0_special_process_count,
                object_l0_stamping_blank_count=classified.counts.object_l0_stamping_blank_count,
                object_l1_subassembly_count=classified.counts.object_l1_subassembly_count,
                object_l1_stamping_count=classified.counts.object_l1_stamping_count,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            )
            db.commit()
            db.refresh(written.header)
            header = written.header
        except BusinessException as exc:
            db.rollback()
            self.log_service.persist_failed(
                db,
                current_user=current_user,
                started_at=started_at,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                snapshot_id=snapshot_id,
                node_count=node_count,
                object_count=object_count,
                other_leaf_count=other_leaf_count,
                anomaly_count=anomaly_count,
                qa_passed=qa_passed,
                error_message=str(exc),
            )
            raise
        except Exception:
            db.rollback()
            logger.exception("生成采购对象列表失败")
            self.log_service.persist_failed(
                db,
                current_user=current_user,
                started_at=started_at,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                snapshot_id=snapshot_id,
                node_count=node_count,
                object_count=object_count,
                other_leaf_count=other_leaf_count,
                anomaly_count=anomaly_count,
                qa_passed=qa_passed,
                error_message="系统错误",
            )
            raise

        return BomProcurementObjectGenerateResultVO(
            header=BomProcurementObjectListVO.model_validate(header),
            object_count=object_count,
            other_leaf_count=other_leaf_count,
            anomaly_count=anomaly_count,
        )

    def _prep_snapshot(self, db: Session, snapshot: BomSnapshot) -> BomProcurementObjectPrepStatsVO:
        nodes = self.node_repo.list_by_snapshot(db, snapshot.id)
        existing = self.repository.get_list_by_snapshot_id(db, snapshot.id)
        approved_count = (
            0 if existing is None else self.repository.count_approved_objects(db, existing.id)
        )
        blocked_message = (
            EC_GATE_FULL_GENERATE if _full_generate_blocked(db, snapshot, nodes) else ""
        )
        return _stats_vo(nodes, approved_count=approved_count, blocked_message=blocked_message)

    def _prep_change_version(
        self,
        db: Session,
        snapshot: BomSnapshot,
        nodes: list[BomNode],
    ) -> BomProcurementObjectPrepStatsVO:
        existing = self.repository.get_list_by_snapshot_id(db, snapshot.id)
        if existing is None:
            return _stats_vo(nodes, approved_count=0, blocked_message=_CHANGE_VERSION_NEEDS_SOP)
        approved_count = self._approved_among(db, existing.id, {node.id for node in nodes})
        return _stats_vo(nodes, approved_count=approved_count, blocked_message="")

    def _replace_snapshot(
        self,
        db: Session,
        *,
        snapshot: BomSnapshot,
        audit: AuditCreateFields,
        operator: str,
    ) -> _Written:
        nodes = self.node_repo.list_by_snapshot(db, snapshot.id)
        if not nodes:
            raise BusinessException("该材料清单没有节点，无法生成采购对象列表")
        if _full_generate_blocked(db, snapshot, nodes):
            raise BusinessException(EC_GATE_FULL_GENERATE, code=409)
        classified = classify_nodes(nodes)
        existing = self.repository.get_list_by_snapshot_id(db, snapshot.id)
        source_ids = {node.id for node in nodes}
        confirm_by_node: ConfirmByNode = {}
        if existing is not None:
            if self.repository.count_approved_objects(db, existing.id):
                raise BusinessException(
                    "该范围已有已审核采购对象，禁止覆盖生成；请先批量反审核",
                    code=409,
                )
            confirm_by_node = self._confirm_for(db, existing.id, source_ids)
            self.repository.delete_list(db, existing)
        header = self.repository.create_list(
            db,
            BomProcurementObjectListWrite(
                snapshot_id=snapshot.id,
                location=snapshot.location,
                vehicle_model=snapshot.vehicle_model,
                bom_version=snapshot.bom_version,
                source_filename=snapshot.source_filename or "",
                qa_passed=classified.qa_passed,
                qa_error_text=classified.qa_error_text,
                l0_count=classified.counts.l0_count,
                l0_with_children_count=classified.counts.l0_with_children_count,
                l2_count=classified.counts.l2_count,
                subassembly_child_sum=classified.counts.subassembly_child_sum,
                object_l0_degenerate_count=classified.counts.object_l0_degenerate_count,
                object_l1_subassembly_count=classified.counts.object_l1_subassembly_count,
                object_l1_stamping_count=classified.counts.object_l1_stamping_count,
                other_leaf_count=classified.counts.other_leaf_count,
                anomaly_count=classified.counts.anomaly_count,
                generated_at=now(),
                generated_by=operator,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            ),
        )
        return _Written(header, classified, len(nodes), confirm_by_node)

    def _replace_change_trees(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> _Written:
        loaded = self._load_change_version_nodes(
            db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
        )
        if loaded is None:
            raise NotFoundException("未找到对应材料清单")
        snapshot, nodes = loaded
        if not nodes:
            raise BusinessException("该材料清单没有节点，无法生成采购对象列表")
        classified = classify_nodes(nodes)
        existing = self.repository.get_list_by_snapshot_id(db, snapshot.id)
        if existing is None:
            raise BusinessException(_CHANGE_VERSION_NEEDS_SOP)
        source_ids = {node.id for node in nodes}
        if self._approved_among(db, existing.id, source_ids):
            raise BusinessException(_APPROVED_BLOCKS_CHANGE, code=409)
        confirm_by_node = self._confirm_for(db, existing.id, source_ids)
        self.repository.delete_objects_by_source_node_ids(
            db, list_id=existing.id, source_node_ids=list(source_ids)
        )
        return _Written(existing, classified, len(nodes), confirm_by_node)

    def _load_change_version_nodes(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> tuple[BomSnapshot, list[BomNode]] | None:
        roots = self.node_repo.list_l0_by_scope_version(
            db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
        )
        if not roots:
            return None
        snapshot_id = roots[0].snapshot_id
        if any(root.snapshot_id != snapshot_id for root in roots):
            raise BusinessException("这个变更版本跨了多份材料清单，不能生成")
        snapshot = BomSnapshotRepository().get_by_id(db, snapshot_id)
        if snapshot is None:
            return None
        all_nodes = self.node_repo.list_by_snapshot(db, snapshot.id)
        keep = descendant_ids(all_nodes, {root.id for root in roots})
        return snapshot, [node for node in all_nodes if node.id in keep]

    def _approved_among(self, db: Session, list_id: int, source_ids: set[int]) -> int:
        return sum(
            1
            for row in self.repository.list_objects_by_list_id(db, list_id)
            if row.source_node_id in source_ids
            and row.section == SECTION_OBJECT
            and row.audit_status == AUDIT_APPROVED
        )

    def _confirm_for(self, db: Session, list_id: int, source_ids: set[int]) -> ConfirmByNode:
        confirm_by_node: ConfirmByNode = {}
        for row in self.repository.list_objects_by_list_id(db, list_id):
            if row.section != SECTION_OBJECT or row.source_node_id not in source_ids:
                continue
            confirm_by_node[row.source_node_id] = (
                row.confirm_status,
                row.confirmed_by,
                row.confirmed_at,
                row.confirm_remark,
                row.supplier_name,
            )
        return confirm_by_node


def _full_generate_blocked(db: Session, snapshot: BomSnapshot, nodes: list[BomNode]) -> bool:
    if not nodes:
        return False
    sop_year, sop_month, _, _ = VehicleModelService().project_sop_period(
        db, snapshot.location, snapshot.vehicle_model
    )
    l0_roots = [
        PeriodRoot(
            effective_year=node.effective_year,
            effective_month=node.effective_month,
            expiry_year=node.expiry_year,
            expiry_month=node.expiry_month,
        )
        for node in nodes
        if int(node.level) == 0
    ]
    return snapshot_blocks_full_generate(l0_roots, sop_year=sop_year, sop_month=sop_month)


def _listed_object_count(classified: ClassifyResult) -> int:
    counts = classified.counts
    return (
        counts.object_l0_degenerate_count
        + counts.object_l1_subassembly_count
        + counts.object_l1_stamping_count
    )


def _stats_vo(
    nodes: list[BomNode],
    *,
    approved_count: int,
    blocked_message: str,
) -> BomProcurementObjectPrepStatsVO:
    classified = classify_nodes(nodes)
    if blocked_message:
        message = blocked_message
    elif approved_count:
        message = _APPROVED_BLOCKS
    elif not nodes:
        message = "该材料清单没有节点"
    else:
        message = ""
    return BomProcurementObjectPrepStatsVO(
        node_count=len(nodes),
        object_count=_listed_object_count(classified),
        other_leaf_count=classified.counts.other_leaf_count,
        anomaly_count=classified.counts.anomaly_count,
        approved_count=approved_count,
        qa_passed=classified.qa_passed,
        ready=approved_count == 0 and len(nodes) > 0 and not blocked_message,
        message=message,
    )
