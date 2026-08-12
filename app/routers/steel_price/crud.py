"""
钢材价格管理 API
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps.auth import get_current_user
from app.common.permissions.checks import require_permission
from app.schemas.common.page_result import PageResult
from app.schemas.dto.steel_price_dto import (
    SteelPriceAuditDTO,
    SteelPriceBatchApproveDTO,
    SteelPriceBatchDeleteDTO,
    SteelPriceBatchReverseAuditDTO,
    SteelPriceQuery,
    SteelPriceReverseAuditDTO,
    SteelPriceUpdate,
)
from app.schemas.vo.steel_price_vo import (
    SteelPriceBatchAuditResultVO,
    SteelPriceBatchDeleteResultVO,
    SteelPriceResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.steel_price import SteelPriceService
from app.services.steel_price.steel_price_export_service import SteelPriceExportService
from app.utils.response import ApiResponse


router = APIRouter(prefix="/api/steel-prices", tags=["钢材价格管理"])

_steel_price_service = SteelPriceService()
_steel_price_export_service = SteelPriceExportService()


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
    current_user: UserVO = Depends(get_current_user),
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
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[SteelPriceBatchDeleteResultVO]:
    """
    按筛选条件批量删除未审核钢材价格。

    年度、月份、基地必填；已审核通过的记录跳过。
    """
    require_permission(current_user, "op:steel-price-list:delete")
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


@router.post(
    "/batch-approve",
    response_model=ApiResponse[SteelPriceBatchAuditResultVO],
)
def batch_approve_steel_prices(
    body: SteelPriceBatchApproveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[SteelPriceBatchAuditResultVO]:
    """
    按年度+月份+基地批量审核通过。

    三者必填；仅处理待审/已驳回，已通过记录跳过。
    """
    require_permission(current_user, "op:steel-price-list:approve")
    result, error = _steel_price_service.batch_approve(db, body, current_user=current_user)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    assert result is not None
    return ApiResponse.ok(
        data=result,
        message=(
            f"已审核通过 {result.updated_count} 条"
            + (
                f"，跳过 {result.skipped_count} 条"
                if result.skipped_count
                else ""
            )
        ),
    )


@router.post(
    "/batch-reverse-audit",
    response_model=ApiResponse[SteelPriceBatchAuditResultVO],
)
def batch_reverse_audit_steel_prices(
    body: SteelPriceBatchReverseAuditDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[SteelPriceBatchAuditResultVO]:
    """
    按年度+月份+基地批量反审核。

    三者必填；仅处理已通过记录，其余跳过；反审核意见必填。
    """
    require_permission(current_user, "op:steel-price-list:reverse")
    result, error = _steel_price_service.batch_reverse_audit(
        db, body, current_user=current_user
    )
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)
    assert result is not None
    return ApiResponse.ok(
        data=result,
        message=(
            f"已反审核 {result.updated_count} 条"
            + (
                f"，跳过 {result.skipped_count} 条"
                if result.skipped_count
                else ""
            )
        ),
    )


@router.get("/export-download")
def export_download(
    year: int | None = Query(None, ge=2000, le=2100, description="年度"),
    month: int | None = Query(None, ge=1, le=12, description="月份"),
    location: str | None = Query(None, description="采购基地"),
    category_name: str | None = Query(None, description="钢种大类"),
    grade: str | None = Query(None, description="牌号（模糊）"),
    steel_mill: str | None = Query(None, description="钢厂"),
    audit_status: str | None = Query(None, description="审核状态"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
) -> StreamingResponse:
    """
    按当前筛选条件导出钢材联动价格 Excel。

    含基价/厚度/宽度/锌层完整溯源（ID + 文件名 + 表页 + 行号 + 列号），便于对账扯皮。
    """
    if not any([year, month, location, category_name, grade, steel_mill, audit_status]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少选择一个筛选条件后再导出",
        )

    content, filename = _steel_price_export_service.export(
        db,
        year=year,
        month=month,
        location=location.strip() if location else None,
        category_name=category_name.strip() if category_name else None,
        grade=grade.strip() if grade else None,
        steel_mill=steel_mill.strip() if steel_mill else None,
        audit_status=audit_status.strip() if audit_status else None,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.get(
    "/{record_id}",
    response_model=ApiResponse[SteelPriceResponse],
)
def get_steel_price(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
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
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[SteelPriceResponse]:
    """更新钢材价格（已审核通过不可改）。"""
    require_permission(current_user, "op:steel-price-list:update")
    record, error = _steel_price_service.update(
        db, record_id, body, current_user=current_user
    )
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
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[None]:
    """删除钢材价格（已审核通过不可删）。"""
    require_permission(current_user, "op:steel-price-list:delete")
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
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[SteelPriceResponse]:
    """经理审核通过。"""
    require_permission(current_user, "op:steel-price-list:approve")
    record, error = _steel_price_service.approve(
        db, record_id, body, current_user=current_user
    )
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
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[SteelPriceResponse]:
    """经理审核驳回。"""
    require_permission(current_user, "op:steel-price-list:reject")
    record, error = _steel_price_service.reject(
        db, record_id, body, current_user=current_user
    )
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
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[SteelPriceResponse]:
    """经理反审核（approved → pending）。"""
    require_permission(current_user, "op:steel-price-list:reverse")
    record, error = _steel_price_service.reverse_audit(
        db, record_id, body, current_user=current_user
    )
    if error:
        _raise_service_error(error)
    return ApiResponse.updated(data=record, message="反审核成功")
