"""
冲压废料月度销售价格路由（以「月」为录入/维护单元）
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.dto.stamping_scrap_price_dto import (
    StampingScrapPriceCopyMonth,
    StampingScrapPriceMonthSaveDTO,
)
from app.schemas.vo.stamping_scrap_price_vo import (
    StampingScrapPriceCopyMonthResponse,
    StampingScrapPriceFilterOptionsVO,
    StampingScrapPriceMonthSheetVO,
    StampingScrapPriceMonthSummaryVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.yishiyiyi.scrap_price import (
    StampingScrapPriceExportService,
    StampingScrapPriceService,
)
from app.utils.response import ApiResponse


router = APIRouter(prefix="/api/yishiyiyi/scrap-price", tags=["废料月度销售价格"])

_scrap_price_service = StampingScrapPriceService()
_scrap_price_export_service = StampingScrapPriceExportService()


@router.get(
    "/month",
    response_model=ApiResponse[StampingScrapPriceMonthSheetVO],
)
def get_month_sheet(
    year: int = Query(..., ge=2000, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SCRAP_PRICE_VIEW)),
) -> ApiResponse[StampingScrapPriceMonthSheetVO]:
    """取某月录入矩阵：固定 6 行（已录数据或空模板）。"""
    data = _scrap_price_service.get_month_sheet(db, year, month)
    return ApiResponse.ok(
        data=data,
        message=(
            f"{year}-{month:02d} "
            f"{'已完整' if data.is_complete else f'已录 {data.filled_count}/6'}"
        ),
    )


@router.put(
    "/month",
    response_model=ApiResponse[StampingScrapPriceMonthSheetVO],
)
def save_month(
    body: StampingScrapPriceMonthSaveDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(Perm.SCRAP_PRICE_CREATE, Perm.SCRAP_PRICE_UPDATE)
    ),
) -> ApiResponse[StampingScrapPriceMonthSheetVO]:
    """整月一次提交：覆盖写入固定 6 个基地。"""
    sheet = _scrap_price_service.save_month(db, body, current_user=current_user)
    return ApiResponse.updated(
        data=sheet,
        message=f"{body.year}-{body.month:02d} 保存成功",
    )


@router.delete(
    "/month",
    response_model=ApiResponse[None],
)
def delete_month(
    year: int = Query(..., ge=2000, le=2100, description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SCRAP_PRICE_DELETE)),
) -> ApiResponse[None]:
    """删除整月数据。"""
    count = _scrap_price_service.delete_month(db, year, month)
    return ApiResponse.deleted(message=f"已删除 {year}-{month:02d} 共 {count} 条")


@router.get(
    "/months",
    response_model=ApiResponse[list[StampingScrapPriceMonthSummaryVO]],
)
def list_months(
    year: int | None = Query(None, ge=2000, le=2100, description="按年筛选"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SCRAP_PRICE_VIEW)),
) -> ApiResponse[list[StampingScrapPriceMonthSummaryVO]]:
    """已维护月份列表（维护页导航）。"""
    data = _scrap_price_service.list_month_summaries(db, year=year)
    return ApiResponse.ok(data=data, message=f"共 {len(data)} 个月份")


@router.get(
    "/filters/options",
    response_model=ApiResponse[StampingScrapPriceFilterOptionsVO],
)
def get_filter_options(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SCRAP_PRICE_VIEW)),
) -> ApiResponse[StampingScrapPriceFilterOptionsVO]:
    """筛选选项：已有年份 + 固定基地清单。"""
    data = _scrap_price_service.get_filter_options(db)
    return ApiResponse.ok(data=data)


@router.get(
    "/export",
    response_model=None,
)
def export_excel(
    year: int | None = Query(None, ge=2000, le=2100, description="仅导出指定年；空则导出全部年份"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SCRAP_PRICE_EXPORT)),
) -> StreamingResponse:
    """导出废料销售价宽表 Excel（跨年空行；有扣费三行 / 无扣费一行）。"""
    content, filename = _scrap_price_export_service.export(db, year=year, current_user=current_user)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/copy-month",
    response_model=ApiResponse[StampingScrapPriceCopyMonthResponse],
)
def copy_month(
    body: StampingScrapPriceCopyMonth,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SCRAP_PRICE_COPY)),
) -> ApiResponse[StampingScrapPriceCopyMonthResponse]:
    """从源月复制到目标月（目标已有则覆盖；源月必须录满 6 行）。"""
    result = _scrap_price_service.copy_month(db, body, current_user=current_user)
    return ApiResponse.ok(
        data=result,
        message=(
            f"从 {body.source_year}-{body.source_month:02d} "
            f"复制到 {body.target_year}-{body.target_month:02d} 成功"
        ),
    )
