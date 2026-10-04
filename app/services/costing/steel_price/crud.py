"""钢材价格：单条查询、改、删与按条件批量删除。"""

from __future__ import annotations

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.costing.steel_price.steel_price_repository import (
    SteelPriceRepository,
)
from app.schemas.dto.steel_price_dto import (
    SteelPriceBatchDeleteDTO,
    SteelPricePatch,
    SteelPriceUpdate,
)
from app.schemas.vo.steel_price_vo import SteelPriceBatchDeleteResultVO, SteelPriceResponse
from app.schemas.vo.user_vo import UserVO
from app.services.costing.steel_price.paginate import attach_mill_abbreviation
from app.services.costing.steel_price.pricing import (
    compute_final_price,
    ensure_not_approved,
)
from app.services.masterdata.steel_mill.service import SteelMillService

logger = logging.getLogger("service.steel_price")


def get_steel_price(
    repository: SteelPriceRepository, db: Session, record_id: int
) -> SteelPriceResponse:
    record = repository.get_by_id(db, record_id)
    if record is None:
        raise NotFoundException("记录不存在")
    return attach_mill_abbreviation(db, [record])[0]


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
        return attach_mill_abbreviation(db, [updated])[0]
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
    steel_mill_id = SteelMillService().filter_id(db, data.steel_mill)

    try:
        skipped_approved_count = repository.count_approved_by_conditions(
            db,
            year=data.year,
            month=data.month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill_id=steel_mill_id,
        )
        deleted_count = repository.delete_unaudited_by_conditions(
            db,
            year=data.year,
            month=data.month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill_id=steel_mill_id,
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
