"""采购对象清单 — 单条确认与按范围批量审核 / 反审核 / 删除。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.bom.procurement_object_repository import (
    BomProcurementObjectRepository,
    object_scope_filters,
)
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectBatchApproveDTO,
    BomProcurementObjectBatchDeleteDTO,
    BomProcurementObjectBatchReverseAuditDTO,
    BomProcurementObjectConfirmDTO,
    BomProcurementObjectSupplierDTO,
)
from app.schemas.vo.bom_procurement_object_vo import (
    BomProcurementObjectBatchAuditResultVO,
    BomProcurementObjectBatchDeleteResultVO,
    BomProcurementObjectVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.procurement_object.classify import SECTION_OBJECT
from app.services.bom.procurement_object.mapping import row_to_vo
from app.services.masterdata.supplier import SupplierService

logger = logging.getLogger("service.bom.procurement_object.audit")

_CONFIRM_STATUSES = frozenset({"pending", "outsourced", "in_house"})


def _optional_bom_version(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


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
        if row.audit_status == AUDIT_APPROVED:
            return row_to_vo(db, self.repository, row)
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
            if status == "in_house":
                row.supplier_name = None
            db.commit()
            db.refresh(row)
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("确认采购对象失败")
            raise
        return row_to_vo(db, self.repository, row)

    def update_supplier(
        self,
        db: Session,
        object_id: int,
        dto: BomProcurementObjectSupplierDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectVO:
        raw = (dto.supplier_name or "").strip() or None
        row = self.repository.get_object_by_id(db, object_id)
        if row is None:
            raise NotFoundException(f"采购对象不存在: id={object_id}")
        if row.section != SECTION_OBJECT:
            raise BusinessException("核对区行禁止指定供应商")
        header = self.repository.get_list_by_id(db, row.list_id)
        if header is None:
            raise NotFoundException("所属采购对象清单不存在")
        if row.audit_status == AUDIT_APPROVED:
            return row_to_vo(db, self.repository, row)
        canonical = None if raw is None else SupplierService().require_enabled(db, raw)
        operator = display_name(current_user)
        try:
            row.supplier_name = canonical
            row.updated_by = operator
            db.commit()
            db.refresh(row)
        except IntegrityError:
            db.rollback()
            raise BusinessException(
                "没有该供应商，请到供应商一览手工增加或上传（#/supplier-list）"
            ) from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新采购对象供应商失败")
            raise
        return row_to_vo(db, self.repository, row)

    def batch_approve(
        self,
        db: Session,
        dto: BomProcurementObjectBatchApproveDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectBatchAuditResultVO:
        location, vehicle_model, bom_version = self._require_location_vehicle(
            db, dto.location, dto.vehicle_model, dto.bom_version
        )
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")
        object_rows = self.repository.list_objects_for_export(
            db,
            scope=object_scope_filters(
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                section=SECTION_OBJECT,
            ),
        )
        pending_ids = [row.id for row in object_rows if row.audit_status == AUDIT_PENDING]
        skipped = sum(1 for row in object_rows if row.audit_status == AUDIT_APPROVED)
        try:
            updated = self.repository.approve_objects_by_ids(
                db,
                object_ids=pending_ids,
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
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: BomProcurementObjectBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectBatchAuditResultVO:
        location, vehicle_model, bom_version = self._require_location_vehicle(
            db, dto.location, dto.vehicle_model, dto.bom_version
        )
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")
        object_rows = self.repository.list_objects_for_export(
            db,
            scope=object_scope_filters(
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                section=SECTION_OBJECT,
            ),
        )
        approved_ids = [row.id for row in object_rows if row.audit_status == AUDIT_APPROVED]
        skipped = sum(1 for row in object_rows if row.audit_status == AUDIT_PENDING)
        try:
            updated = self.repository.reverse_objects_by_ids(
                db,
                object_ids=approved_ids,
                reverse_audited_by=operator,
                reverse_audited_at=now(),
                reverse_audit_remark=dto.reverse_audit_remark.strip(),
                updated_by=operator,
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("批量反审核采购对象失败")
            raise
        return BomProcurementObjectBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def batch_delete(
        self,
        db: Session,
        dto: BomProcurementObjectBatchDeleteDTO,
        current_user: UserVO,
    ) -> BomProcurementObjectBatchDeleteResultVO:
        """按基地+项目删除；有版本或有已审时只删命中 pending。"""
        location, vehicle_model, bom_version = self._require_location_vehicle(
            db, dto.location, dto.vehicle_model, dto.bom_version
        )
        headers = self.repository.list_lists_by_location_vehicle(
            db, location=location, vehicle_model=vehicle_model
        )
        _ = current_user
        try:
            if bom_version:
                rows = self.repository.list_objects_for_export(
                    db,
                    scope=object_scope_filters(
                        location=location,
                        vehicle_model=vehicle_model,
                        bom_version=bom_version,
                    ),
                )
                skipped = sum(1 for row in rows if row.audit_status == AUDIT_APPROVED)
                pending_ids = [row.id for row in rows if row.audit_status == AUDIT_PENDING]
                deleted = self.repository.delete_pending_objects_by_ids(db, pending_ids)
                touched_list_ids = {row.list_id for row in rows}
                for header in headers:
                    if header.id in touched_list_ids:
                        self.repository.recount_header_from_rows(db, header)
            else:
                skipped = sum(
                    self.repository.count_approved_objects(db, header.id) for header in headers
                )
                if skipped:
                    deleted = 0
                    for header in headers:
                        deleted += self.repository.delete_pending_objects_by_list_id(db, header.id)
                        self.repository.recount_header_from_rows(db, header)
                else:
                    deleted = 0
                    for header in headers:
                        deleted += len(self.repository.list_objects_by_list_id(db, header.id))
                        self.repository.delete_list(db, header)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("批量删除采购对象失败")
            raise
        return BomProcurementObjectBatchDeleteResultVO(
            deleted_count=deleted,
            skipped_approved_count=skipped,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def _require_location_vehicle(
        self,
        db: Session,
        location: str,
        vehicle_model: str,
        bom_version: str | None,
    ) -> tuple[str, str, str | None]:
        location_text = location.strip()
        model_text = vehicle_model.strip()
        version_text = _optional_bom_version(bom_version)
        headers = self.repository.list_lists_by_location_vehicle(
            db, location=location_text, vehicle_model=model_text
        )
        if not headers:
            raise NotFoundException("尚未生成采购对象清单")
        return location_text, model_text, version_text
