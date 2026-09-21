"""钢材价格：单条与批量审核 / 驳回 / 反审核。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED, display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.costing.steel_price.steel_price_repository import (
    SteelPriceRepository,
)
from app.schemas.dto.steel_price_dto import (
    SteelPriceAuditDTO,
    SteelPriceBatchApproveDTO,
    SteelPriceBatchReverseAuditDTO,
    SteelPriceReverseAuditDTO,
)
from app.schemas.vo.steel_price_vo import SteelPriceBatchAuditResultVO, SteelPriceResponse
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.steel_price")


def batch_approve_steel_prices(
    repository: SteelPriceRepository,
    db: Session,
    data: SteelPriceBatchApproveDTO,
    current_user: UserVO,
) -> SteelPriceBatchAuditResultVO:
    """按年度+月份+基地批量审核通过。仅更新 pending / rejected；已通过记录计入 skipped。"""
    location = data.location.strip()
    if not location:
        raise BusinessException("采购基地不能为空")
    audited_by = display_name(current_user)
    if not audited_by:
        raise BusinessException("无法识别当前登录用户")
    audit_remark = data.audit_remark.strip()
    if not audit_remark:
        raise BusinessException("审核意见必填")

    try:
        skipped_count = repository.count_by_conditions_and_statuses(
            db,
            year=data.year,
            month=data.month,
            location=location,
            statuses=[AUDIT_APPROVED],
        )
        updated_count = repository.approve_by_period(
            db,
            year=data.year,
            month=data.month,
            location=location,
            audited_by=audited_by,
            audited_at=now(),
            audit_remark=audit_remark,
            updated_by=audited_by,
        )
        db.commit()
        return SteelPriceBatchAuditResultVO(
            updated_count=updated_count,
            skipped_count=skipped_count,
            year=data.year,
            month=data.month,
            location=location,
        )
    except Exception:
        db.rollback()
        logger.exception(
            "批量审核失败: year=%s month=%s location=%s",
            data.year,
            data.month,
            location,
        )
        raise


def batch_reverse_audit_steel_prices(
    repository: SteelPriceRepository,
    db: Session,
    data: SteelPriceBatchReverseAuditDTO,
    current_user: UserVO,
) -> SteelPriceBatchAuditResultVO:
    """按年度+月份+基地批量反审核。仅更新 approved → pending；非已通过计入 skipped。"""
    location = data.location.strip()
    if not location:
        raise BusinessException("采购基地不能为空")
    reverse_audited_by = display_name(current_user)
    if not reverse_audited_by:
        raise BusinessException("无法识别当前登录用户")
    reverse_audit_remark = data.reverse_audit_remark.strip()
    if not reverse_audit_remark:
        raise BusinessException("反审核原因必填")

    try:
        skipped_count = repository.count_by_conditions_and_statuses(
            db,
            year=data.year,
            month=data.month,
            location=location,
            statuses=[AUDIT_PENDING, AUDIT_REJECTED],
        )
        updated_count = repository.reverse_audit_by_period(
            db,
            year=data.year,
            month=data.month,
            location=location,
            reverse_audited_by=reverse_audited_by,
            reverse_audited_at=now(),
            reverse_audit_remark=reverse_audit_remark,
            updated_by=reverse_audited_by,
        )
        db.commit()
        return SteelPriceBatchAuditResultVO(
            updated_count=updated_count,
            skipped_count=skipped_count,
            year=data.year,
            month=data.month,
            location=location,
        )
    except Exception:
        db.rollback()
        logger.exception(
            "批量反审核失败: year=%s month=%s location=%s",
            data.year,
            data.month,
            location,
        )
        raise


def approve_steel_price(
    repository: SteelPriceRepository,
    db: Session,
    record_id: int,
    data: SteelPriceAuditDTO,
    current_user: UserVO,
) -> SteelPriceResponse:
    record = repository.get_by_id(db, record_id)
    if record is None:
        raise NotFoundException("记录不存在")
    if record.audit_status == AUDIT_APPROVED:
        raise BusinessException("记录已是审核通过状态")
    if record.audit_status not in (AUDIT_PENDING, AUDIT_REJECTED):
        raise BusinessException(f"当前状态不允许审核通过: {record.audit_status}")

    try:
        operator_name = display_name(current_user)
        updated = repository.update(
            db,
            record_id,
            {
                "audit_status": AUDIT_APPROVED,
                "audited_by": operator_name,
                "audited_at": now(),
                "audit_remark": data.audit_remark,
                "updated_by": operator_name,
            },
        )
        if updated is None:
            raise NotFoundException("记录不存在")
        db.commit()
        db.refresh(updated)
        return SteelPriceResponse.model_validate(updated)
    except (BusinessException, NotFoundException):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("审核通过失败: id=%s", record_id)
        raise


def reject_steel_price(
    repository: SteelPriceRepository,
    db: Session,
    record_id: int,
    data: SteelPriceAuditDTO,
    current_user: UserVO,
) -> SteelPriceResponse:
    record = repository.get_by_id(db, record_id)
    if record is None:
        raise NotFoundException("记录不存在")
    if record.audit_status == AUDIT_APPROVED:
        raise BusinessException("已通过记录请先反审核，再驳回")
    if record.audit_status != AUDIT_PENDING:
        raise BusinessException(f"当前状态不允许驳回: {record.audit_status}")

    try:
        operator_name = display_name(current_user)
        updated = repository.update(
            db,
            record_id,
            {
                "audit_status": AUDIT_REJECTED,
                "audited_by": operator_name,
                "audited_at": now(),
                "audit_remark": data.audit_remark,
                "updated_by": operator_name,
            },
        )
        if updated is None:
            raise NotFoundException("记录不存在")
        db.commit()
        db.refresh(updated)
        return SteelPriceResponse.model_validate(updated)
    except (BusinessException, NotFoundException):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("审核驳回失败: id=%s", record_id)
        raise


def reverse_audit_steel_price(
    repository: SteelPriceRepository,
    db: Session,
    record_id: int,
    data: SteelPriceReverseAuditDTO,
    current_user: UserVO,
) -> SteelPriceResponse:
    record = repository.get_by_id(db, record_id)
    if record is None:
        raise NotFoundException("记录不存在")
    if record.audit_status != AUDIT_APPROVED:
        raise BusinessException("仅已通过记录可以反审核")

    try:
        operator_name = display_name(current_user)
        updated = repository.update(
            db,
            record_id,
            {
                "audit_status": AUDIT_PENDING,
                "reverse_audited_by": operator_name,
                "reverse_audited_at": now(),
                "reverse_audit_remark": data.reverse_audit_remark.strip(),
                "updated_by": operator_name,
            },
        )
        if updated is None:
            raise NotFoundException("记录不存在")
        db.commit()
        db.refresh(updated)
        return SteelPriceResponse.model_validate(updated)
    except (BusinessException, NotFoundException):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("反审核失败: id=%s", record_id)
        raise
