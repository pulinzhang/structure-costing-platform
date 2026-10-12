"""采购对象列表 — 生成批次日志。"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.common.timezone import now
from app.exceptions.base import NotFoundException
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectGenerateLogQuery,
    BomProcurementObjectGenerateLogWrite,
)
from app.schemas.vo.bom_procurement_object_vo import BomProcurementObjectGenerateLogVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object.classify import (
    KIND_L0_DEGENERATE,
    KIND_L1_STAMPING,
    KIND_L1_SUBASSEMBLY,
    SECTION_ANOMALY,
    SECTION_OBJECT,
    SECTION_OTHER_LEAF,
    SUBTYPE_SPECIAL_PROCESS,
    SUBTYPE_STAMPING_BLANK,
)
from app.services.bom.procurement_object.labels import (
    KIND_LABELS,
    SECTION_LABELS,
    SUBTYPE_LABELS,
)

logger = logging.getLogger("service.bom.procurement_object.generate.log")

STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"


class BomProcurementObjectGenerateLogService:
    def __init__(self) -> None:
        self.repository = BomProcurementObjectRepository()

    def list_logs(
        self,
        db: Session,
        query: BomProcurementObjectGenerateLogQuery,
    ) -> tuple[list[BomProcurementObjectGenerateLogVO], int]:
        skip = (query.page - 1) * query.size
        records, total = self.repository.paginate_generate_logs(
            db,
            location=query.location,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            skip=skip,
            limit=query.size,
        )
        return [BomProcurementObjectGenerateLogVO.model_validate(row) for row in records], total

    def get_log(self, db: Session, log_id: int) -> BomProcurementObjectGenerateLogVO:
        record = self.repository.get_generate_log_by_id(db, log_id)
        if record is None:
            raise NotFoundException(f"生成日志不存在: id={log_id}")
        return BomProcurementObjectGenerateLogVO.model_validate(record)

    def write_success(
        self,
        db: Session,
        *,
        current_user: UserVO,
        started_at: datetime,
        finished_at: datetime,
        location: str,
        vehicle_model: str,
        bom_version: str,
        snapshot_id: int | None,
        node_count: int,
        object_count: int,
        other_leaf_count: int,
        anomaly_count: int,
        qa_passed: bool,
        object_l0_degenerate_count: int,
        object_l0_special_process_count: int,
        object_l0_stamping_blank_count: int,
        object_l1_subassembly_count: int,
        object_l1_stamping_count: int,
        created_by: str | None,
        updated_by: str | None,
    ) -> None:
        operator = display_name(current_user)
        self.repository.create_generate_log(
            db,
            self._log_write(
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                snapshot_id=snapshot_id,
                status=STATUS_SUCCESS,
                node_count=node_count,
                object_count=object_count,
                other_leaf_count=other_leaf_count,
                anomaly_count=anomaly_count,
                qa_passed=qa_passed,
                detail_text=self._success_detail(
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                    node_count=node_count,
                    object_count=object_count,
                    other_leaf_count=other_leaf_count,
                    anomaly_count=anomaly_count,
                    qa_passed=qa_passed,
                    object_l0_degenerate_count=object_l0_degenerate_count,
                    object_l0_special_process_count=object_l0_special_process_count,
                    object_l0_stamping_blank_count=object_l0_stamping_blank_count,
                    object_l1_subassembly_count=object_l1_subassembly_count,
                    object_l1_stamping_count=object_l1_stamping_count,
                ),
                started_at=started_at,
                finished_at=finished_at,
                current_user=current_user,
                operator=operator,
                created_by=created_by,
                updated_by=updated_by,
            ),
        )

    def persist_failed(
        self,
        db: Session,
        *,
        current_user: UserVO,
        started_at: datetime,
        location: str,
        vehicle_model: str,
        bom_version: str,
        snapshot_id: int | None,
        node_count: int,
        object_count: int,
        other_leaf_count: int,
        anomaly_count: int,
        qa_passed: bool,
        error_message: str,
    ) -> None:
        try:
            audit = audit_create(current_user)
            operator = display_name(current_user)
            self.repository.create_generate_log(
                db,
                self._log_write(
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                    snapshot_id=snapshot_id,
                    status=STATUS_FAILED,
                    node_count=node_count,
                    object_count=object_count,
                    other_leaf_count=other_leaf_count,
                    anomaly_count=anomaly_count,
                    qa_passed=qa_passed,
                    detail_text=(
                        f"范围：{location} / {vehicle_model} / {bom_version}\n"
                        f"失败：{error_message}"
                    ),
                    started_at=started_at,
                    finished_at=now(),
                    current_user=current_user,
                    operator=operator,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("写入采购对象生成失败日志失败")

    def _log_write(
        self,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        snapshot_id: int | None,
        status: str,
        node_count: int,
        object_count: int,
        other_leaf_count: int,
        anomaly_count: int,
        qa_passed: bool,
        detail_text: str,
        started_at: datetime,
        finished_at: datetime | None,
        current_user: UserVO,
        operator: str | None,
        created_by: str | None,
        updated_by: str | None,
    ) -> BomProcurementObjectGenerateLogWrite:
        return BomProcurementObjectGenerateLogWrite(
            calc_batch_id=f"po-gen-{uuid.uuid4().hex[:16]}",
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            snapshot_id=snapshot_id,
            status=status,
            node_count=node_count,
            object_count=object_count,
            other_leaf_count=other_leaf_count,
            anomaly_count=anomaly_count,
            qa_passed=qa_passed,
            detail_text=detail_text,
            started_at=started_at,
            finished_at=finished_at,
            operator_id=current_user.id,
            operator_name=operator,
            created_by=created_by,
            updated_by=updated_by,
        )

    @staticmethod
    def _success_detail(
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        node_count: int,
        object_count: int,
        other_leaf_count: int,
        anomaly_count: int,
        qa_passed: bool,
        object_l0_degenerate_count: int,
        object_l0_special_process_count: int,
        object_l0_stamping_blank_count: int,
        object_l1_subassembly_count: int,
        object_l1_stamping_count: int,
    ) -> str:
        qa_label = "通过" if qa_passed else "未通过"
        special_label = SUBTYPE_LABELS[SUBTYPE_SPECIAL_PROCESS]
        blank_label = SUBTYPE_LABELS[SUBTYPE_STAMPING_BLANK]
        return (
            f"这次生成的是：{location}，{vehicle_model}，版本 {bom_version}。\n"
            f"材料清单 {node_count} 行。\n"
            f"检查{qa_label}。\n"
            f"{SECTION_LABELS[SECTION_OBJECT]} {object_count} 个"
            f"（{KIND_LABELS[KIND_L0_DEGENERATE]} {object_l0_degenerate_count}，"
            f"{KIND_LABELS[KIND_L1_SUBASSEMBLY]} {object_l1_subassembly_count}，"
            f"{KIND_LABELS[KIND_L1_STAMPING]} {object_l1_stamping_count}）。\n"
            f"其中 {special_label} {object_l0_special_process_count} 个，"
            f"{blank_label} {object_l0_stamping_blank_count} 个。\n"
            f"{blank_label} {object_l0_stamping_blank_count} 个可以发货。"
            "材料清单上没写焊接信息的，不算处理费。\n"
            f"{SECTION_LABELS[SECTION_OTHER_LEAF]} {other_leaf_count} 个。\n"
            f"{SECTION_LABELS[SECTION_ANOMALY]} {anomaly_count} 个。"
        )
