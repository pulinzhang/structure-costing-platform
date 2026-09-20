"""采购对象清单 — 从材料清单树生成。

列入规则在 classify：退化仅 L0（无子件，或全部 L1 无内部号）。L1 有内部号才列入采购对象。

找 snapshot（§13 干净库）：写路径 require_enabled + normalize_vehicle_model + 精确匹配；
prep 同 normalize、不强制 require_enabled。禁止在本文件 expand 基地别名。
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.engineering_change_gates import (
    EC_GATE_FULL_GENERATE,
    PeriodRoot,
    snapshot_blocks_full_generate,
)
from app.common.timezone import now
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException
from app.repositories.bom.bom.node import BomNodeRepository
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
from app.services.bom.procurement_object.classify import SECTION_OBJECT, classify_nodes
from app.services.bom.procurement_object.generate_log_service import (
    BomProcurementObjectGenerateLogService,
)
from app.services.bom.procurement_object.row_write import ConfirmByNode, build_object_row_write
from app.services.bom.procurement_object.snapshot_scope import lookup_snapshot, require_snapshot
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.vehicle_model import VehicleModelService

logger = logging.getLogger("service.bom.procurement_object.generate")


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
        if snapshot is None:
            return BomProcurementObjectPrepStatsVO(
                message="未找到对应材料清单，请先上传 BOM",
            )
        nodes = self.node_repo.list_by_snapshot(db, snapshot.id)
        classified = classify_nodes(nodes)
        existing = self.repository.get_list_by_snapshot_id(db, snapshot.id)
        approved_count = 0
        if existing is not None:
            approved_count = self.repository.count_approved_objects(db, existing.id)
        ready = approved_count == 0 and len(nodes) > 0
        message = ""
        if approved_count:
            message = "该范围已有已审核采购对象，须先批量反审核后再生成"
        elif not nodes:
            message = "该材料清单没有节点"
        return BomProcurementObjectPrepStatsVO(
            node_count=len(nodes),
            object_count=classified.counts.object_l0_degenerate_count
            + classified.counts.object_l1_subassembly_count
            + classified.counts.object_l1_stamping_count,
            other_leaf_count=classified.counts.other_leaf_count,
            anomaly_count=classified.counts.anomaly_count,
            approved_count=approved_count,
            qa_passed=classified.qa_passed,
            ready=ready,
            message=message,
        )

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
        operator = display_name(current_user)

        try:
            snapshot = require_snapshot(
                db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
            )
            snapshot_id = snapshot.id
            nodes = self.node_repo.list_by_snapshot(db, snapshot.id)
            node_count = len(nodes)
            if not nodes:
                raise BusinessException("该材料清单没有节点，无法生成采购对象清单")
            sop_year, sop_month, _, _ = VehicleModelService().project_sop_period(
                db, location, vehicle_model
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
            if snapshot_blocks_full_generate(
                l0_roots,
                sop_year=sop_year,
                sop_month=sop_month,
            ):
                raise BusinessException(EC_GATE_FULL_GENERATE, code=409)
            # 列入：退化仅 L0；L1 有内部号才进采购对象。规则在 classify。
            classified = classify_nodes(nodes)
            qa_passed = classified.qa_passed
            object_count = (
                classified.counts.object_l0_degenerate_count
                + classified.counts.object_l1_subassembly_count
                + classified.counts.object_l1_stamping_count
            )
            other_leaf_count = classified.counts.other_leaf_count
            anomaly_count = classified.counts.anomaly_count
            existing = self.repository.get_list_by_snapshot_id(db, snapshot.id)
            confirm_by_node: ConfirmByNode = {}
            if existing is not None:
                approved = self.repository.count_approved_objects(db, existing.id)
                if approved:
                    raise BusinessException(
                        "该范围已有已审核采购对象，禁止覆盖生成；请先批量反审核",
                        code=409,
                    )
                for row in self.repository.list_objects_by_list_id(db, existing.id):
                    if row.section != SECTION_OBJECT:
                        continue
                    confirm_by_node[row.source_node_id] = (
                        row.confirm_status,
                        row.confirmed_by,
                        row.confirmed_at,
                        row.confirm_remark,
                        row.supplier_name,
                    )

            generated_at = now()
            if existing is not None:
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
                    generated_at=generated_at,
                    generated_by=operator,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            payloads = [
                build_object_row_write(
                    db,
                    classified_row,
                    list_id=header.id,
                    confirm_by_node=confirm_by_node,
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
            db.refresh(header)
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
            logger.exception("生成采购对象清单失败")
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
