"""采购对象清单 — 从材料清单树生成。

列入规则在 classify：退化仅 L0（无子件，或全部 L1 无内部号）。L1 有内部号才列入采购对象。
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_PENDING, audit_create, display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom.node import BomSnapshot
from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectGenerateDTO,
    BomProcurementObjectListWrite,
    BomProcurementObjectPrepQuery,
    BomProcurementObjectWrite,
)
from app.schemas.vo.bom_procurement_object_vo import (
    BomProcurementObjectGenerateResultVO,
    BomProcurementObjectListVO,
    BomProcurementObjectPrepStatsVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object.classify import (
    SECTION_OBJECT,
    ClassifiedRow,
    classify_nodes,
)
from app.services.bom.procurement_object.generate_log_service import (
    BomProcurementObjectGenerateLogService,
)
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.supplier import SupplierService

logger = logging.getLogger("service.bom.procurement_object.generate")


class BomProcurementObjectGenerateService:
    def __init__(self) -> None:
        self.snapshot_repo = BomSnapshotRepository()
        self.node_repo = BomNodeRepository()
        self.repository = BomProcurementObjectRepository()
        self.log_service = BomProcurementObjectGenerateLogService()

    def prep_stats(
        self, db: Session, query: BomProcurementObjectPrepQuery
    ) -> BomProcurementObjectPrepStatsVO:
        location = (query.location or "").strip()
        vehicle_model = (query.vehicle_model or "").strip()
        bom_version = (query.bom_version or "").strip()
        if not location or not vehicle_model or not bom_version:
            return BomProcurementObjectPrepStatsVO(
                message="请选定基地 / 项目 / 版本",
            )
        snapshot = self.snapshot_repo.get_by_unique_key(db, location, vehicle_model, bom_version)
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
        vehicle_model = dto.vehicle_model.strip()
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
            snapshot = self._require_snapshot(db, location, vehicle_model, bom_version)
            snapshot_id = snapshot.id
            nodes = self.node_repo.list_by_snapshot(db, snapshot.id)
            node_count = len(nodes)
            if not nodes:
                raise BusinessException("该材料清单没有节点，无法生成采购对象清单")
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
            confirm_by_node: dict[
                int, tuple[str, str | None, datetime | None, str | None, str | None]
            ] = {}
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
                self._row_write(
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

    def _require_snapshot(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomSnapshot:
        snapshot = self.snapshot_repo.get_by_unique_key(
            db, location.strip(), vehicle_model.strip(), bom_version.strip()
        )
        if snapshot is None:
            raise NotFoundException("未找到对应材料清单")
        return snapshot

    def _row_write(
        self,
        db: Session,
        row: ClassifiedRow,
        *,
        list_id: int,
        confirm_by_node: dict[int, tuple[str, str | None, datetime | None, str | None, str | None]],
        created_by: str | None,
        updated_by: str | None,
    ) -> BomProcurementObjectWrite:
        confirm_status = "pending"
        confirmed_by = None
        confirmed_at = None
        confirm_remark = None
        supplier_name = None
        if row.section == SECTION_OBJECT and row.source_node_id in confirm_by_node:
            (
                confirm_status,
                confirmed_by,
                confirmed_at,
                confirm_remark,
                supplier_name,
            ) = confirm_by_node[row.source_node_id]
        if (
            confirm_status == "in_house"
            or supplier_name
            and not SupplierService().is_registered(db, supplier_name)
        ):
            supplier_name = None
        return BomProcurementObjectWrite(
            list_id=list_id,
            section=row.section,
            object_kind=row.object_kind,
            degenerate_subtype=row.degenerate_subtype,
            source_node_id=row.source_node_id,
            part_number=row.part_number,
            part_name=row.part_name,
            internal_number=row.internal_number,
            level=row.level,
            node_role=row.node_role,
            qty=row.qty,
            qty_unit=row.qty_unit,
            l0_part_number=row.l0_part_number,
            l0_part_name=row.l0_part_name,
            parent_part_number=row.parent_part_number,
            parent_part_name=row.parent_part_name,
            excel_filename=row.excel_filename,
            excel_sheet_name=row.excel_sheet_name,
            excel_row=row.excel_row,
            child_count=row.child_count,
            weld_info=row.weld_info,
            remark=row.remark,
            has_outsource_remark=row.has_outsource_remark,
            material=row.material,
            thickness_text=row.thickness_text,
            material_mill=row.material_mill,
            data_gap=row.data_gap,
            alert_code=row.alert_code,
            confirm_status=confirm_status,
            confirmed_by=confirmed_by,
            confirmed_at=confirmed_at,
            confirm_remark=confirm_remark,
            supplier_name=supplier_name,
            audit_status=AUDIT_PENDING,
            created_by=created_by,
            updated_by=updated_by,
        )
