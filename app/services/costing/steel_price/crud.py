"""钢材价格：单条增删改与按条件批量删除。"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import AUDIT_PENDING, audit_create, display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.costing.steel_price.steel_price_repository import (
    SteelPriceRepository,
)
from app.schemas.dto.steel_price_dto import (
    SteelPriceBatchDeleteDTO,
    SteelPriceCreate,
    SteelPricePatch,
    SteelPriceUpdate,
    SteelPriceWrite,
)
from app.schemas.vo.steel_price_vo import SteelPriceBatchDeleteResultVO, SteelPriceResponse
from app.schemas.vo.user_vo import UserVO
from app.services.costing.steel_price.pricing import (
    FORMULA_VERSION,
    build_spec_or_none,
    compute_final_price,
    ensure_not_approved,
)
from app.services.settings.logical_ref.service import ensure_logical_deletable

logger = logging.getLogger("service.steel_price")


def get_steel_price(
    repository: SteelPriceRepository, db: Session, record_id: int
) -> SteelPriceResponse:
    record = repository.get_by_id(db, record_id)
    if record is None:
        raise NotFoundException("记录不存在")
    return SteelPriceResponse.model_validate(record)


def create_steel_price(
    repository: SteelPriceRepository,
    db: Session,
    data: SteelPriceCreate,
    current_user: UserVO,
) -> SteelPriceResponse:
    current_time = now()
    audit = audit_create(current_user)
    write = SteelPriceWrite(
        year=data.year,
        month=data.month,
        location=data.location,
        steel_mill=data.steel_mill,
        category_name=data.category_name,
        grade=data.grade,
        thickness=data.thickness,
        width=data.width,
        spec=build_spec_or_none(data.thickness, data.width, data.spec),
        base_price=data.base_price,
        thickness_adjustment=data.thickness_adjustment,
        width_adjustment=data.width_adjustment,
        zinc_adjustment=data.zinc_adjustment,
        processing_fee=data.processing_fee,
        other_adjustment=data.other_adjustment,
        final_price_per_ton=compute_final_price(
            base_price=data.base_price,
            thickness_adjustment=data.thickness_adjustment,
            width_adjustment=data.width_adjustment,
            zinc_adjustment=data.zinc_adjustment,
            processing_fee=data.processing_fee,
            other_adjustment=data.other_adjustment,
        ),
        calc_batch_id=f"manual-{uuid.uuid4().hex[:16]}",
        match_status="manual",
        calc_status="success",
        calc_message=None,
        formula_version=FORMULA_VERSION,
        calculated_at=current_time,
        audit_status=AUDIT_PENDING,
        remark=data.remark,
        created_by=audit["created_by"],
        updated_by=audit["updated_by"],
    )

    try:
        record = repository.create(db, write)
        db.commit()
        db.refresh(record)
        return SteelPriceResponse.model_validate(record)
    except IntegrityError as error:
        db.rollback()
        message = (
            f"该业务键已存在：{write.year}-{write.month:02d}/"
            f"{write.location}/{write.steel_mill}/"
            f"{write.category_name}/{write.grade}/"
            f"{write.thickness}*{write.width}"
        )
        logger.warning("创建钢材价格冲突: %s, error=%s", message, error)
        raise BusinessException(message) from error
    except BusinessException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("创建钢材价格失败")
        raise


def update_steel_price(
    repository: SteelPriceRepository,
    db: Session,
    record_id: int,
    data: SteelPriceUpdate,
    current_user: UserVO,
) -> SteelPriceResponse:
    record = repository.get_by_id(db, record_id)
    if record is None:
        raise NotFoundException("记录不存在")

    ensure_not_approved(record)

    payload: SteelPricePatch = {}
    if data.base_price is not None:
        payload["base_price"] = data.base_price
    if data.thickness_adjustment is not None:
        payload["thickness_adjustment"] = data.thickness_adjustment
    if data.width_adjustment is not None:
        payload["width_adjustment"] = data.width_adjustment
    if data.zinc_adjustment is not None:
        payload["zinc_adjustment"] = data.zinc_adjustment
    if data.processing_fee is not None:
        payload["processing_fee"] = data.processing_fee
    if data.other_adjustment is not None:
        payload["other_adjustment"] = data.other_adjustment
    if data.spec is not None:
        payload["spec"] = data.spec
    if data.remark is not None:
        payload["remark"] = data.remark
    if not payload:
        raise BusinessException("未提供任何可更新字段")

    payload["updated_by"] = display_name(current_user)
    payload["final_price_per_ton"] = compute_final_price(
        base_price=payload.get("base_price", record.base_price),
        thickness_adjustment=payload.get("thickness_adjustment", record.thickness_adjustment),
        width_adjustment=payload.get("width_adjustment", record.width_adjustment),
        zinc_adjustment=payload.get("zinc_adjustment", record.zinc_adjustment),
        processing_fee=payload.get("processing_fee", record.processing_fee),
        other_adjustment=payload.get("other_adjustment", record.other_adjustment),
    )

    try:
        updated = repository.update(db, record_id, payload)
        if updated is None:
            db.rollback()
            raise NotFoundException("记录不存在")
        db.commit()
        db.refresh(updated)
        return SteelPriceResponse.model_validate(updated)
    except IntegrityError as error:
        db.rollback()
        logger.warning("更新钢材价格冲突: id=%s, error=%s", record_id, error)
        raise BusinessException("更新违反唯一约束") from error
    except (BusinessException, NotFoundException):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("更新钢材价格失败: id=%s", record_id)
        raise


def delete_steel_price(repository: SteelPriceRepository, db: Session, record_id: int) -> None:
    record = repository.get_by_id(db, record_id)
    if record is None:
        raise NotFoundException("记录不存在")

    ensure_not_approved(record)

    ensure_logical_deletable(
        db,
        "steel_prices",
        [{"id": record_id}],
        subject="该钢材联动价",
    )

    try:
        success = repository.delete(db, record_id)
        if not success:
            db.rollback()
            raise NotFoundException("记录不存在")
        db.commit()
    except (BusinessException, NotFoundException):
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("删除钢材价格失败: id=%s", record_id)
        raise


def batch_delete_steel_prices(
    repository: SteelPriceRepository,
    db: Session,
    data: SteelPriceBatchDeleteDTO,
) -> SteelPriceBatchDeleteResultVO:
    """按筛选条件批量删除未审核记录。年度 / 月份 / 基地必填；已审核通过的记录跳过不删。"""
    location = data.location.strip()
    if not location:
        raise BusinessException("基地不能为空")

    category_name = data.category_name.strip() if data.category_name else None
    grade = data.grade.strip() if data.grade else None
    steel_mill = data.steel_mill.strip() if data.steel_mill else None

    try:
        skipped_approved_count = repository.count_approved_by_conditions(
            db,
            year=data.year,
            month=data.month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
        )
        record_ids = repository.list_unaudited_ids(
            db,
            year=data.year,
            month=data.month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
        )
        ensure_logical_deletable(
            db,
            "steel_prices",
            [{"id": record_id} for record_id in record_ids],
            subject="该钢材联动价",
        )
        deleted_count = repository.delete_unaudited_by_conditions(
            db,
            year=data.year,
            month=data.month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
        )
        db.commit()
        message = f"已删除 {deleted_count} 条未审核记录"
        if skipped_approved_count:
            message += f"，跳过已审核 {skipped_approved_count} 条"
        return SteelPriceBatchDeleteResultVO(
            deleted_count=deleted_count,
            skipped_approved_count=skipped_approved_count,
            year=data.year,
            month=data.month,
            location=location,
            message=message,
        )
    except Exception:
        db.rollback()
        logger.exception(
            "批量删除钢材价格失败: year=%s month=%s location=%s",
            data.year,
            data.month,
            location,
        )
        raise
