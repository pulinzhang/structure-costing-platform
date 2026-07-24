"""
吨位价格路由
Stamping API - API 接口
"""

from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.stamping import StampingTonnagePriceService
from app.schemas.stamping import (
    StampingTonnagePriceCreate,
    StampingTonnagePriceUpdate,
    StampingTonnagePriceQuery,
    StampingTonnagePriceBulkCreate,
    StampingTonnagePriceCopyTemplate,
)
from app.utils.response import ApiResponse


logger = logging.getLogger("router.stamping.tonnage_price")
router = APIRouter(prefix="/api/stamping/tonnage-price", tags=["冲压吨位价格 API"])

_stamping_tonnage_price_service = StampingTonnagePriceService()


@router.get("/list")
def list_tonnage_prices(
    year: int | None = None,
    db: Session = Depends(get_db),
):
    """
    获取吨位价格列表（按年份筛选）
    """
    if year:
        records = _stamping_tonnage_price_service.list_by_year(db, year)
        return ApiResponse.success(
            data=records,
            message=f"查询到 {len(records)} 条记录",
        )
    # 不带 year：一次性返回所有年份的记录，避免 N+1
    records = _stamping_tonnage_price_service.list_all(db)
    return ApiResponse.success(
        data=records,
        message=f"查询到 {len(records)} 条记录",
    )


@router.get("")
def get_tonnage_prices(
    query: StampingTonnagePriceQuery = Depends(),
    db: Session = Depends(get_db),
):
    """
    分页获取吨位价格列表
    """
    data, total, filters = _stamping_tonnage_price_service.paginate(db, query)
    return ApiResponse.list_(
        data=data,
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 条记录",
        filters=filters,
    )


@router.get("/{record_id}")
def get_tonnage_price(
    record_id: int,
    db: Session = Depends(get_db),
):
    """
    获取单条吨位价格记录
    """
    record = _stamping_tonnage_price_service.get_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return ApiResponse.success(data=record)


@router.post("")
def create_tonnage_price(
    body: StampingTonnagePriceCreate,
    db: Session = Depends(get_db),
):
    """
    创建吨位价格记录
    """
    record, error = _stamping_tonnage_price_service.create(db, body)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.success(data=record, message="创建成功")


@router.post("/bulk")
def bulk_create_tonnage_prices(
    body: StampingTonnagePriceBulkCreate,
    db: Session = Depends(get_db),
):
    """
    批量创建吨位价格记录
    """
    created, skipped, failed = _stamping_tonnage_price_service.bulk_create(
        db, body.items
    )
    return ApiResponse.success(
        data={
            "created": created,
            "skipped": skipped,
            "failed": failed,
        },
        message=f"创建成功 {len(created)} 条，跳过 {len(skipped)} 条，失败 {len(failed)} 条",
    )


@router.put("/{record_id}")
def update_tonnage_price(
    record_id: int,
    body: StampingTonnagePriceUpdate,
    db: Session = Depends(get_db),
):
    """
    更新吨位价格记录
    """
    record, error = _stamping_tonnage_price_service.update(db, record_id, body)
    if error:
        # "记录不存在" → 404；数据库/校验失败 → 500
        if "记录不存在" in error:
            raise HTTPException(status_code=404, detail=error)
        logger.error("更新吨位价格失败: id=%s, error=%s", record_id, error)
        raise HTTPException(status_code=500, detail=error)
    return ApiResponse.success(data=record, message="更新成功")


@router.delete("/{record_id}")
def delete_tonnage_price(
    record_id: int,
    db: Session = Depends(get_db),
):
    """
    删除吨位价格记录
    """
    success, error = _stamping_tonnage_price_service.delete(db, record_id)
    if not success:
        if "记录不存在" in (error or ""):
            raise HTTPException(status_code=404, detail=error or "记录不存在")
        logger.error("删除吨位价格失败: id=%s, error=%s", record_id, error)
        raise HTTPException(status_code=500, detail=error or "删除失败")
    return ApiResponse.deleted(message="删除成功")


@router.post("/copy")
def copy_tonnage_price_template(
    body: StampingTonnagePriceCopyTemplate,
    db: Session = Depends(get_db),
):
    """
    从指定年份复制价格模板到目标年份
    """
    created, skipped, failed = _stamping_tonnage_price_service.copy_from_year(
        db, body.source_year, body.target_year
    )
    return ApiResponse.success(
        data={
            "created": created,
            "skipped": skipped,
            "failed": failed,
        },
        message=f"从 {body.source_year} 年复制到 {body.target_year} 年：创建 {created} 条",
    )


@router.get("/options/years")
def get_year_options(
    db: Session = Depends(get_db),
):
    """
    获取年份下拉选项
    """
    years = _stamping_tonnage_price_service.get_years(db)
    # 确保包含当前年份和下一年
    current_year = datetime.now().year
    if current_year not in years:
        years.insert(0, current_year)
    if current_year + 1 not in years:
        years.insert(0, current_year + 1)
    return ApiResponse.success(data=sorted(set(years), reverse=True))
