"""
钢材价格管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common.page_result import PageResult
from app.schemas.dto.steel_price_dto import (
    SteelPriceAuditDTO,
    SteelPriceBatchDeleteDTO,
    SteelPriceQuery,
    SteelPriceReverseAuditDTO,
    SteelPriceUpdate,
)
from app.schemas.vo.steel_price_vo import (
    SteelPriceBatchDeleteResultVO,
    SteelPriceResponse,
)
from app.services.steel_price import SteelPriceService
from app.utils.response import ApiResponse


router = APIRouter(prefix="/api/steel-prices", tags=["钢材价格管理"])

_steel_price_service = SteelPriceService()


def _raise_service_error(error: str | None, not_found_prefix: str = "记录不存在") -> None:
    if not error:
        return
    if error.startswith(not_found_prefix) or "不存在" in error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)


@router.get(
    "",
    response_model=ApiResponse[PageResult[SteelPriceResponse]],
)
def list_steel_prices(
    query: SteelPriceQuery = Depends(),
    db: Session = Depends(get_db),
) -> ApiResponse[PageResult[SteelPriceResponse]]:
    """分页浏览钢材价格。"""
    records, total, filters = _steel_price_service.paginate(db, query)
    return ApiResponse.list_(
        items=records,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters.model_dump(),
    )


@router.post(
    "/batch-delete",
    response_model=ApiResponse[SteelPriceBatchDeleteResultVO],
)
def batch_delete_steel_prices(
    body: SteelPriceBatchDeleteDTO,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceBatchDeleteResultVO]:
    """
    按筛选条件批量删除未审核钢材价格。

    年度、月份、基地必填；已审核通过的记录跳过。
    """
    result, error = _steel_price_service.batch_delete(db, body)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    assert result is not None
    return ApiResponse.ok(
        data=result,
        message=(
            f"已删除 {result.deleted_count} 条未审核记录"
            + (
                f"，跳过已审核 {result.skipped_approved_count} 条"
                if result.skipped_approved_count
                else ""
            )
        ),
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    return ApiResponse.ok(data=record)


@router.put(
    "/{record_id}",
    response_model=ApiResponse[SteelPriceResponse],
)
def update_steel_price(
    record_id: int,
    body: SteelPriceUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceResponse]:
    """更新钢材价格（已审核通过不可改）。"""
    record, error = _steel_price_service.update(db, record_id, body)
    if error:
        _raise_service_error(error)
    return ApiResponse.updated(data=record, message="更新成功")


@router.delete(
    "/{record_id}",
    response_model=ApiResponse[None],
)
def delete_steel_price(
    record_id: int,
    db: Session = Depends(get_db),
) -> ApiResponse[None]:
    """删除钢材价格（已审核通过不可删）。"""
    success, error = _steel_price_service.delete(db, record_id)
    if not success:
        _raise_service_error(error or "记录不存在")
    return ApiResponse.deleted(message="删除成功")


@router.post(
    "/{record_id}/approve",
    response_model=ApiResponse[SteelPriceResponse],
)
def approve_steel_price(
    record_id: int,
    body: SteelPriceAuditDTO,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceResponse]:
    """经理审核通过。"""
    record, error = _steel_price_service.approve(db, record_id, body)
    if error:
        _raise_service_error(error)
    return ApiResponse.updated(data=record, message="审核通过")


@router.post(
    "/{record_id}/reject",
    response_model=ApiResponse[SteelPriceResponse],
)
def reject_steel_price(
    record_id: int,
    body: SteelPriceAuditDTO,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceResponse]:
    """经理审核驳回。"""
    record, error = _steel_price_service.reject(db, record_id, body)
    if error:
        _raise_service_error(error)
    return ApiResponse.updated(data=record, message="已驳回")


@router.post(
    "/{record_id}/reverse-audit",
    response_model=ApiResponse[SteelPriceResponse],
)
def reverse_audit_steel_price(
    record_id: int,
    body: SteelPriceReverseAuditDTO,
    db: Session = Depends(get_db),
) -> ApiResponse[SteelPriceResponse]:
    """经理反审核（approved → pending）。"""
    record, error = _steel_price_service.reverse_audit(db, record_id, body)
    if error:
        _raise_service_error(error)
    return ApiResponse.updated(data=record, message="反审核成功")
