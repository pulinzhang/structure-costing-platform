"""
仪表盘路由
Dashboard Router - API 接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.utils.logging_config import get_logger
from app.database import get_db
from app.models.stamping import StampingPart, StampingProcess
from app.schemas.vo.dashboard_vo import (
    CountResponse,
    DashboardStatsVO,
    SteelPriceCalcStatsVO,
)
from app.services.dashboard.dashboard_service import DashboardService
from app.utils.response import ApiResponse


logger = get_logger("router.dashboard")
router = APIRouter(prefix="/api/dashboard", tags=["仪表盘 API"])


@router.get("/stats/parts", response_model=ApiResponse[CountResponse])
def get_parts_count(db: Session = Depends(get_db)) -> ApiResponse[CountResponse]:
    """
    获取零件总数
    """
    try:
        count = db.query(StampingPart).count()
        return ApiResponse.ok(data=CountResponse(count=count), message="获取成功")
    except Exception as e:
        logger.error(f"获取零件总数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/processes", response_model=ApiResponse[CountResponse])
def get_processes_count(db: Session = Depends(get_db)) -> ApiResponse[CountResponse]:
    """
    获取工序总数
    """
    try:
        count = db.query(StampingProcess).count()
        return ApiResponse.ok(data=CountResponse(count=count), message="获取成功")
    except Exception as e:
        logger.error(f"获取工序总数失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/models", response_model=ApiResponse[CountResponse])
def get_models_count(db: Session = Depends(get_db)) -> ApiResponse[CountResponse]:
    """
    获取车型数量
    """
    try:
        count = db.query(StampingPart.vehicle_model).distinct().count()
        return ApiResponse.ok(data=CountResponse(count=count), message="获取成功")
    except Exception as e:
        logger.error(f"获取车型数量失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
) -> ApiResponse[SteelPriceCalcStatsVO]:
    """
    钢价联动计算页数据依据统计：
    中标基价库 / 厚宽调价规则 / 厚度规格行数
    """
    try:
        service = DashboardService()
        stats = service.get_steel_price_calc_stats(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
        )
        return ApiResponse.ok(data=stats, message="获取成功")
    except Exception as e:
        logger.error(f"获取钢价计算统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=ApiResponse[DashboardStatsVO])
def get_all_stats(db: Session = Depends(get_db)) -> ApiResponse[DashboardStatsVO]:
    """
    获取仪表盘全部统计数据
    """
    try:
        parts_count = db.query(StampingPart).count()
        processes_count = db.query(StampingProcess).count()
        models_count = db.query(StampingPart.vehicle_model).distinct().count()

        return ApiResponse.ok(
            data=DashboardStatsVO(
                total_parts=parts_count,
                total_processes=processes_count,
                total_models=models_count,
                recent_uploads=[],
            ),
            message="获取成功",
        )
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
