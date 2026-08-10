"""
冲次费率路由
API 接口定义
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.stamping.tonnage_price_service import StampingTonnagePriceService
from app.schemas.dto.stamping_tonnage_price_dto import (
    StampingTonnagePriceCreate,
    StampingTonnagePriceUpdate,
    StampingTonnagePriceQuery,
)
from app.schemas.vo.stamping_tonnage_price_vo import (
    StampingTonnagePriceResponse,
    StampingTonnagePriceBulkCreateResponse,
    StampingTonnagePriceCopyYearResponse,
)
from app.schemas.common.page_result import PageResult
from app.utils.response import ApiResponse


router = APIRouter(prefix="/api/stamping/tonnage-price", tags=["冲次费率 API"])

_tonnage_price_service = StampingTonnagePriceService()


@router.get("/list", response_model=ApiResponse[List[StampingTonnagePriceResponse]])
def list_all(db: Session = Depends(get_db)):
    """获取所有冲次费率列表（按年份、吨位排序）"""
    data = _tonnage_price_service.list_all(db)
    return ApiResponse.ok(data=data, message=f"查询到 {len(data)} 条记录")


@router.get("/by-year/{year}", response_model=ApiResponse[List[StampingTonnagePriceResponse]])
def list_by_year(year: int, db: Session = Depends(get_db)):
    """获取指定年份的所有冲次费率"""
    data = _tonnage_price_service.list_by_year(db, year)
    return ApiResponse.ok(data=data, message=f"查询到 {len(data)} 条记录")


@router.get("/paginate", response_model=ApiResponse[PageResult[StampingTonnagePriceResponse]])
def paginate(
    query: StampingTonnagePriceQuery = Depends(),
    db: Session = Depends(get_db),
):
    """分页查询冲次费率"""
    rows, total, filters = _tonnage_price_service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message=f"查询到 {total} 条记录",
    )


@router.get("/{id}", response_model=ApiResponse[StampingTonnagePriceResponse])
def get_by_id(id: int, db: Session = Depends(get_db)):
    """获取单个冲次费率记录"""
    record = _tonnage_price_service.get_by_id(db, id)
    if not record:
        raise HTTPException(status_code=404, detail=f"冲次费率记录不存在: id={id}")
    return ApiResponse.ok(data=record, message="获取成功")


@router.post("", response_model=ApiResponse[StampingTonnagePriceResponse])
def create(
    body: StampingTonnagePriceCreate,
    db: Session = Depends(get_db),
):
    """创建冲次费率记录"""
    record, error = _tonnage_price_service.create(db, body)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.created(data=record, message="创建成功")


@router.post("/bulk", response_model=ApiResponse[StampingTonnagePriceBulkCreateResponse])
def bulk_create(
    items: List[StampingTonnagePriceCreate],
    db: Session = Depends(get_db),
):
    """批量创建冲次费率记录"""
    created, skipped, failed = _tonnage_price_service.bulk_create(db, items)
    return ApiResponse.ok(
        data=StampingTonnagePriceBulkCreateResponse(
            created=created,
            skipped=skipped,
            failed=failed,
            created_count=len(created),
            skipped_count=len(skipped),
            failed_count=len(failed),
        ),
        message=f"批量创建完成: 成功 {len(created)}, 跳过 {len(skipped)}, 失败 {len(failed)}",
    )


@router.put("/{id}", response_model=ApiResponse[StampingTonnagePriceResponse])
def update(
    id: int,
    body: StampingTonnagePriceUpdate,
    db: Session = Depends(get_db),
):
    """更新冲次费率记录"""
    record, error = _tonnage_price_service.update(db, id, body)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return ApiResponse.ok(data=record, message="更新成功")


@router.delete("/{id}", response_model=ApiResponse[None])
def delete(id: int, db: Session = Depends(get_db)):
    """删除冲次费率记录"""
    success, error = _tonnage_price_service.delete(db, id)
    if not success:
        raise HTTPException(status_code=404, detail=error or "记录不存在")
    return ApiResponse.deleted(message="删除成功")


@router.post("/copy-year", response_model=ApiResponse[StampingTonnagePriceCopyYearResponse])
def copy_from_year(
    source_year: int,
    target_year: int,
    db: Session = Depends(get_db),
):
    """从源年份复制价格到目标年份"""
    created, skipped, failed = _tonnage_price_service.copy_from_year(
        db, source_year, target_year
    )
    return ApiResponse.ok(
        data=StampingTonnagePriceCopyYearResponse(
            source_year=source_year,
            target_year=target_year,
            created_count=created,
            skipped_count=skipped,
            failed=failed,
        ),
        message=f"从 {source_year} 复制到 {target_year}: 成功 {created}, 跳过 {skipped}",
    )


@router.get("/filters/years", response_model=ApiResponse[List[int]])
def get_years(db: Session = Depends(get_db)):
    """获取所有年份列表"""
    data = _tonnage_price_service.get_years(db)
    return ApiResponse.ok(data=data)


@router.get("/filters/tonnages", response_model=ApiResponse[List[int]])
def get_tonnages(db: Session = Depends(get_db)):
    """获取所有吨位列表"""
    data = _tonnage_price_service.get_tonnages(db)
    return ApiResponse.ok(data=data)
