"""采购对象清单 — 单条确认与按范围批量审核 / 反审核 / 删除。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom.procurement_object import BomProcurementObjectList
from app.repositories.bom.procurement_object_repository import BomProcurementObjectRepository
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectBatchApproveDTO,
    BomProcurementObjectBatchDeleteDTO,
    BomProcurementObjectBatchReverseAuditDTO,
    BomProcurementObjectConfirmDTO,
)
from app.schemas.vo.bom_procurement_object_vo import (
    BomProcurementObjectBatchAuditResultVO,
    BomProcurementObjectBatchDeleteResultVO,
    BomProcurementObjectVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object.classify import SECTION_OBJECT
from app.services.bom.procurement_object.mapping import to_object_vo

logger = logging.getLogger("service.bom.procurement_object.audit")

_CONFIRM_STATUSES = frozenset({"pending", "outsourced", "in_house"})


class BomProcurementObjectAuditService:
    def __init__(self) -> None:
        self.repository = BomProcurementObjectRepository()

    def confirm(
        self,
        db: Session,
        object_id: int,
        dto: BomProcurementObjectConfirmDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectVO:
        status = (dto.confirm_status or "").strip()
        if status not in _CONFIRM_STATUSES:
            raise BusinessException("确认状态须为待定、外发或自制")
        row = self.repository.get_object_by_id(db, object_id)
        if row is None:
            raise NotFoundException(f"采购对象不存在: id={object_id}")
        if row.section != SECTION_OBJECT:
            raise BusinessException("核对区行禁止确认")
        header = self.repository.get_list_by_id(db, row.list_id)
        if header is None:
            raise NotFoundException("所属采购对象清单不存在")
        if not header.qa_passed:
            raise BusinessException("检测未通过，禁止确认")
        if row.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核记录禁止改确认，请先批量反审核")
        operator = display_name(current_user)
        try:
            row.confirm_status = status
            row.confirm_remark = (dto.confirm_remark or "").strip() or None
            row.updated_by = operator
            if status == "pending":
                row.confirmed_by = None
                row.confirmed_at = None
            else:
                row.confirmed_by = operator
                row.confirmed_at = now()
            db.commit()
            db.refresh(row)
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("确认采购对象失败")
            raise
        return to_object_vo(row)

    def batch_approve(
        self,
        db: Session,
        dto: BomProcurementObjectBatchApproveDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectBatchAuditResultVO:
        header = self._require_header(db, dto.location, dto.vehicle_model, dto.bom_version)
        if not header.qa_passed:
            raise BusinessException("检测未通过，禁止审核")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")
        try:
            skipped = self.repository.count_approved_objects(db, header.id)
            updated = self.repository.approve_objects_by_list_id(
                db,
                list_id=header.id,
                audited_by=operator,
                audited_at=now(),
                audit_remark=dto.audit_remark.strip(),
                updated_by=operator,
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("批量审核采购对象失败")
            raise
        return BomProcurementObjectBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=header.location,
            vehicle_model=header.vehicle_model,
            bom_version=header.bom_version,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: BomProcurementObjectBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectBatchAuditResultVO:
        header = self._require_header(db, dto.location, dto.vehicle_model, dto.bom_version)
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")
        try:
            updated = self.repository.reverse_objects_by_list_id(
                db,
                list_id=header.id,
                reverse_audited_by=operator,
                reverse_audited_at=now(),
                reverse_audit_remark=dto.reverse_audit_remark.strip(),
                updated_by=operator,
            )
            skipped = self.repository.summarize_objects(
                db,
                location=header.location,
                vehicle_model=header.vehicle_model,
                bom_version=header.bom_version,
                section=SECTION_OBJECT,
                audit_status=AUDIT_PENDING,
            )["pending_count"]
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("批量反审核采购对象失败")
            raise
        return BomProcurementObjectBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=header.location,
            vehicle_model=header.vehicle_model,
            bom_version=header.bom_version,
        )

    def batch_delete(
        self,
        db: Session,
        dto: BomProcurementObjectBatchDeleteDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectBatchDeleteResultVO:
        header = self._require_header(db, dto.location, dto.vehicle_model, dto.bom_version)
        _ = current_user
        try:
            skipped = self.repository.count_approved_objects(db, header.id)
            deleted = self.repository.delete_pending_objects_by_list_id(db, header.id)
            self.repository.recount_header_from_rows(db, header)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("批量删除采购对象失败")
            raise
        return BomProcurementObjectBatchDeleteResultVO(
            deleted_count=deleted,
            skipped_approved_count=skipped,
            location=header.location,
            vehicle_model=header.vehicle_model,
            bom_version=header.bom_version,
        )

    def _require_header(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomProcurementObjectList:
        header = self.repository.get_list_by_scope(
            db,
            location=location.strip(),
            vehicle_model=vehicle_model.strip(),
            bom_version=bom_version.strip(),
        )
        if header is None:
            raise NotFoundException("尚未生成采购对象清单")
        return header
