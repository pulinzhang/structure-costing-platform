"""
焊接工艺拆解 — 范围审核 / 反审核 / 批量删除

范围键：location + vehicle_model + bom_version
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownBatchApproveDTO,
    BomWeldingProcessBreakdownBatchReverseAuditDTO,
)
from app.schemas.vo.bom_welding_process_breakdown_vo import (
    BomWeldingProcessBreakdownBatchAuditResultVO,
    BomWeldingProcessBreakdownBatchDeleteResultVO,
)
from app.schemas.vo.user_vo import UserVO

WELDING_FEE_REFERENCED = "仍被焊接费引用，请先删除对应焊接费后再删"


def _normalize_scope(
    location: str, vehicle_model: str, bom_version: str
) -> tuple[str, str, str] | None:
    location = (location or "").strip()
    vehicle_model = (vehicle_model or "").strip()
    bom_version = (bom_version or "").strip()
    if not location or not vehicle_model or not bom_version:
        return None
    return location, vehicle_model, bom_version


class BomWeldingProcessBreakdownAuditService:
    """按清单范围的批量删除 / 审核 / 反审核"""

    def __init__(self) -> None:
        self.repository = BomWeldingProcessBreakdownRepository()

    def batch_delete(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomWeldingProcessBreakdownBatchDeleteResultVO:
        scope = _normalize_scope(location, vehicle_model, bom_version)
        if not scope:
            raise BusinessException("基地、项目、版本均必填")
        location, vehicle_model, bom_version = scope

        existing_count = self.repository.count_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        if existing_count <= 0:
            raise BusinessException(
                f"范围「{location}/{vehicle_model}/{bom_version}」没有可删除的数据"
            )

        skipped = self.repository.count_by_scope_and_statuses(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            statuses=[AUDIT_APPROVED],
        )
        try:
            deleted = self.repository.delete_unaudited_by_scope(
                db,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException(WELDING_FEE_REFERENCED) from None
        return BomWeldingProcessBreakdownBatchDeleteResultVO(
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            deleted_count=deleted,
            skipped_approved_count=skipped,
            message=(
                f"已删除 {deleted} 条主表" + (f"，跳过已审核 {skipped} 条" if skipped else "")
            ),
        )

    def batch_approve(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownBatchApproveDTO,
        current_user: UserVO,
    ) -> BomWeldingProcessBreakdownBatchAuditResultVO:
        scope = _normalize_scope(dto.location, dto.vehicle_model, dto.bom_version)
        if not scope:
            raise BusinessException("基地、项目、版本均必填")
        location, vehicle_model, bom_version = scope
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        skipped = self.repository.count_by_scope_and_statuses(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            statuses=[AUDIT_APPROVED],
        )
        updated = self.repository.approve_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            audited_by=operator,
            audited_at=now(),
            audit_remark=(dto.audit_remark or "").strip() or None,
            updated_by=operator,
        )
        db.commit()
        return BomWeldingProcessBreakdownBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: BomWeldingProcessBreakdownBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> BomWeldingProcessBreakdownBatchAuditResultVO:
        scope = _normalize_scope(dto.location, dto.vehicle_model, dto.bom_version)
        if not scope:
            raise BusinessException("基地、项目、版本均必填")
        location, vehicle_model, bom_version = scope
        remark = (dto.reverse_audit_remark or "").strip()
        if not remark:
            raise BusinessException("反审核原因必填")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        skipped = self.repository.count_by_scope_and_statuses(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            statuses=[AUDIT_PENDING],
        )
        updated = self.repository.reverse_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            reverse_audited_by=operator,
            reverse_audited_at=now(),
            reverse_audit_remark=remark,
            updated_by=operator,
        )
        db.commit()
        return BomWeldingProcessBreakdownBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
