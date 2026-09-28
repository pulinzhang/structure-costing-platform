"""
焊接工艺拆解 — 范围审核 / 反审核 / 批量删除

范围键：location + vehicle_model + 树根版本字（节点范围由 BOM 服务给出）。
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
from app.services.bom.bom.period import BomPeriodService
from app.services.settings.schema_comment.service import STILL_REFERENCED, ensure_deletable


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
        source_node_ids = (
            BomPeriodService().node_ids_for_l0_version(
                db,
                bom_version=bom_version,
                location=location,
                vehicle_model=vehicle_model,
            )
            or set()
        )

        existing_count = self.repository.count_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
        )
        if existing_count <= 0:
            raise BusinessException(
                f"范围「{location}/{vehicle_model}/{bom_version}」没有可删除的数据"
            )

        skipped = self.repository.count_by_scope_and_statuses(
            db,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            statuses=[AUDIT_APPROVED],
        )
        node_ids = self.repository.list_unaudited_ids(
            db,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
        )
        try:
            if node_ids:
                ensure_deletable(
                    db,
                    "bom_welding_process_breakdown_node",
                    [{"id": node_id} for node_id in node_ids],
                    subject="这些焊接工艺拆解",
                )
            deleted = self.repository.delete_unaudited_by_scope(
                db,
                location=location,
                vehicle_model=vehicle_model,
                source_node_ids=source_node_ids,
            )
            db.commit()
        except IntegrityError:
            db.rollback()
            raise BusinessException(STILL_REFERENCED) from None
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
        source_node_ids = (
            BomPeriodService().node_ids_for_l0_version(
                db,
                bom_version=bom_version,
                location=location,
                vehicle_model=vehicle_model,
            )
            or set()
        )

        skipped = self.repository.count_by_scope_and_statuses(
            db,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            statuses=[AUDIT_APPROVED],
        )
        updated = self.repository.approve_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
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
        source_node_ids = (
            BomPeriodService().node_ids_for_l0_version(
                db,
                bom_version=bom_version,
                location=location,
                vehicle_model=vehicle_model,
            )
            or set()
        )

        skipped = self.repository.count_by_scope_and_statuses(
            db,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            statuses=[AUDIT_PENDING],
        )
        updated = self.repository.reverse_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
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
