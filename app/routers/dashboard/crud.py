"""
仪表盘路由
Dashboard Router - API 接口

- GET /stats                 仪表盘汇总 KPI
- GET /stats/steel-price-calc 钢价联动计算页数据依据（计算页专用）
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.vo.dashboard_vo import (
    DashboardStatsVO,
    SteelPriceCalcStatsVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.dashboard.dashboard_service import DashboardService
from app.utils.response import ApiResponse


router = APIRouter(prefix="/api/dashboard", tags=["仪表盘 API"])

_dashboard_service = DashboardService()


@router.get("/stats", response_model=ApiResponse[DashboardStatsVO])
def get_all_stats(
    year: int | None = Query(None, ge=2000, le=2100, description="核价年度"),
    month: int | None = Query(None, ge=1, le=12, description="核价月份"),
    location: str | None = Query(None, description="生产基地（空=全部）"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.DASHBOARD_VIEW)),
) -> ApiResponse[DashboardStatsVO]:
    """获取仪表盘汇总：作用域 KPI + 核价流水线就绪度"""
    return ApiResponse.ok(
        data=_dashboard_service.get_all_stats(
            db,
            year=year,
            month=month,
            location=location,
        ),
        message="获取成功",
    )


@router.get(
    "/stats/steel-price-calc",
    response_model=ApiResponse[SteelPriceCalcStatsVO],
)
def get_steel_price_calc_stats(
    year: int = Query(..., ge=2000, le=2100, description="核价年度"),
    month: int = Query(..., ge=1, le=12, description="核价月份"),
    location: str | None = Query(None, description="生产基地"),
    stamping_supplier: str | None = Query(None, description="冲压工厂"),
    vehicle_model: str | None = Query(None, description="配套车型"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_VIEW)),
) -> ApiResponse[SteelPriceCalcStatsVO]:
    """钢价联动计算页数据依据统计"""
    stats = _dashboard_service.get_steel_price_calc_stats(
        db,
        year=year,
        month=month,
        location=location,
        stamping_supplier=stamping_supplier,
        vehicle_model=vehicle_model,
    )
    return ApiResponse.ok(data=stats, message="获取成功")
