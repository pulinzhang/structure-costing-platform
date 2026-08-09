"""
仪表盘路由
Dashboard Router - API 接口
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.utils.logging_config import get_logger
from app.database import get_db
from app.models.stamping import StampingPart, StampingProcess
from app.utils.response import ApiResponse


logger = get_logger("router.dashboard")
router = APIRouter(prefix="/api/dashboard", tags=["仪表盘 API"])


@router.get("/stats/parts")
def get_parts_count(db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """
    获取零件总数
    """
    try:
        count = db.query(StampingPart).count()
        return ApiResponse.ok(data={"count": count}, message="获取成功")
    except Exception as e:
        logger.error(f"获取零件总数失败: {e}")
        return ApiResponse.fail(message=str(e), data={"count": 0})


@router.get("/stats/processes")
def get_processes_count(db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """
    获取工序总数
    """
    try:
        count = db.query(StampingProcess).count()
        return ApiResponse.ok(data={"count": count}, message="获取成功")
    except Exception as e:
        logger.error(f"获取工序总数失败: {e}")
        return ApiResponse.fail(message=str(e), data={"count": 0})


@router.get("/stats/models")
def get_models_count(db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """
    获取车型数量
    """
    try:
        count = db.query(StampingPart.vehicle_model).distinct().count()
        return ApiResponse.ok(data={"count": count}, message="获取成功")
    except Exception as e:
        logger.error(f"获取车型数量失败: {e}")
        return ApiResponse.fail(message=str(e), data={"count": 0})


@router.get("/stats")
def get_all_stats(db: Session = Depends(get_db)) -> ApiResponse[dict]:
    """
    获取仪表盘全部统计数据
    """
    try:
        parts_count = db.query(StampingPart).count()
        processes_count = db.query(StampingProcess).count()
        models_count = db.query(StampingPart.vehicle_model).distinct().count()

        return ApiResponse.ok(
            data={
                "total_parts": parts_count,
                "total_processes": processes_count,
                "total_models": models_count,
                "recent_uploads": [],
            },
            message="获取成功",
        )
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        return ApiResponse.fail(
            message=str(e),
            data={
                "total_parts": 0,
                "total_processes": 0,
                "total_models": 0,
                "recent_uploads": [],
            },
        )
