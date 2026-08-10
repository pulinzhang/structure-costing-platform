"""
钢材价格管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common.page_result import PageResult
from app.schemas.dto.steel_price_dto import (
    SteelPriceCreate,
    SteelPriceQuery,
    SteelPriceUpdate,
)
from app.schemas.vo.steel_price_vo import SteelPriceResponse
from app.services.steel_price import SteelPriceService
from app.utils.response import ApiResponse


router = APIRouter(prefix="/api/steel-prices", tags=["钢材价格管理"])

_steel_price_service = SteelPriceService()


@router.get(
    "",
    response_model=ApiResponse[PageResult[SteelPriceResponse]],
)
def list_steel_prices(
    query: SteelPriceQuery = Depends(),
    db: Session = Depends(get_db),
) -> ApiResponse[PageResult[SteelPriceResponse]]:
    """分页浏览钢材价格。"""
    records, total, _ = _steel_price_service.paginate(db, query)
    return ApiResponse.list_(
        items=records,
        total=total,
        page=query.page,
        page_size=query.size,
    )


@router.get(
    "/{record_id}",
    response_model=ApiResponse[SteelPriceResponse],
)
def get_steel_price(
    record_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceResponse]:
    """查看单条钢材价格。"""
    record = _steel_price_service.get_by_id(db, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="记录不存在")
    return ApiResponse.ok(data=record)


@router.post(
    "",
    response_model=ApiResponse[SteelPriceResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_steel_price(
    body: SteelPriceCreate,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceResponse]:
    """新增钢材价格。"""
    record, error = _steel_price_service.create(db, body)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.created(data=record, message="新增成功")


@router.put(
    "/{record_id}",
    response_model=ApiResponse[SteelPriceResponse],
)
def update_steel_price(
    record_id: int,
    body: SteelPriceUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceResponse]:
    """更新钢材价格。"""
    record, error = _steel_price_service.update(db, record_id, body)
    if error:
        if "不存在" in (error or ""):
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=400, detail=error)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete(
    "/{record_id}",
    response_model=ApiResponse[None],
)
def delete_steel_price(
    record_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    """删除钢材价格。"""
    success, error = _steel_price_service.delete(db, record_id)
    if not success:
        raise HTTPException(status_code=404, detail=error or "记录不存在")
    return ApiResponse.deleted(message="删除成功")