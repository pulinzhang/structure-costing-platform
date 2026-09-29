"""
中标钢厂厚度价格列表路由
预览默认按当年收窄（年度可改/可清空）；年 / 月 / 基地 / 钢厂 / 分类 / 牌号可选。导出须选定年度和月份（一事一议按月定价）。
"""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
    MONTH_MAX,
    MONTH_MIN,
)
from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.vo.steel_base_price_vo import SteelBasePriceFilterOptionsVO
from app.schemas.vo.user_vo import UserVO
from app.schemas.vo.winning_thickness_vo import WinningThicknessRowVO
from app.services.yishiyiyi.base_price.service import SteelBasePriceService
from app.services.yishiyiyi.winning_thickness.export.service import (
    WinningThicknessExportService,
)
from app.utils.logging_config import get_logger
from app.utils.response import ApiResponse

logger = get_logger("router.winning_thickness")

DEFAULT_PREVIEW_PAGE_SIZE = 500

router = APIRouter(prefix="/api/yishiyiyi/winning-thickness", tags=["中标钢厂厚度价格列表"])

_export_service = WinningThicknessExportService()
_base_price_service = SteelBasePriceService()


@router.get(
    "/options",
    response_model=ApiResponse[SteelBasePriceFilterOptionsVO],
    summary="筛选下拉（复用基准价维度）",
)
def get_options(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.WINNING_THICKNESS_DOWNLOAD_VIEW,
            Perm.BASE_PRICE_DOWNLOAD_VIEW,
        )
    ),
) -> ApiResponse[SteelBasePriceFilterOptionsVO]:
    """筛选下拉（复用基准价维度）。"""
    return ApiResponse.ok(data=_base_price_service.get_filter_options(db))


@router.get(
    "/export-preview",
    response_model=ApiResponse[PageResult[WinningThicknessRowVO]],
    summary="预览中标钢厂厚度价格列表",
)
def export_preview(
    year: int | None = Query(None, ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="年度"),
    month: int | None = Query(None, ge=MONTH_MIN, le=MONTH_MAX, description="月份"),
    location: str | None = Query(None, description="基地"),
    steel_mill: str | None = Query(None, description="钢厂"),
    category_name: str | None = Query(None, description="档案大类：冷轧/镀锌/酸洗"),
    grade: str | None = Query(None, description="牌号（档案模糊筛选）"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(DEFAULT_PREVIEW_PAGE_SIZE, ge=1, le=5000, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.WINNING_THICKNESS_DOWNLOAD_VIEW)),
) -> ApiResponse[PageResult[WinningThicknessRowVO]]:
    """预览中标钢厂厚度价格列表。"""
    items, total = _export_service.preview(
        db,
        year=year,
        month=month,
        location=location.strip() if location else None,
        steel_mill=steel_mill,
        category_name=category_name,
        grade=grade,
        page=page,
        page_size=size,
    )

    return ApiResponse.list_(
        items=items,
        total=total,
        page=page,
        page_size=size,
        message="查询成功",
    )


@router.get(
    "/export-download",
    response_model=None,
    summary="下载中标钢厂厚度价格列表 Excel",
)
def export_download(
    year: int | None = Query(None, ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="年度"),
    month: int | None = Query(None, ge=MONTH_MIN, le=MONTH_MAX, description="月份"),
    location: str | None = Query(None, description="基地"),
    steel_mill: str | None = Query(None, description="钢厂"),
    category_name: str | None = Query(None, description="档案大类：冷轧/镀锌/酸洗"),
    grade: str | None = Query(None, description="牌号（档案模糊筛选）"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.WINNING_THICKNESS_DOWNLOAD_EXPORT)),
) -> StreamingResponse:
    """下载中标钢厂厚度价格列表 Excel（一览 + 计算用 + 使用示例）。"""
    content, filename = _export_service.export(
        db,
        year=year,
        month=month,
        location=location.strip() if location else None,
        steel_mill=steel_mill,
        category_name=category_name,
        grade=grade,
        current_user=current_user,
    )

    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
