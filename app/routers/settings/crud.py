"""
设置路由
Settings Router - API 接口
"""

from fastapi import APIRouter

from app.utils.logging_config import get_logger


logger = get_logger("router.settings")
router = APIRouter(prefix="/api/settings", tags=["系统设置 API"])


@router.get("/config")
async def get_config():
    """
    获取系统配置
    """
    logger.info("获取系统配置")
    return {
        "success": True,
        "message": "获取成功",
        "data": {
            "app_name": "汽车冲压件自动核价平台",
            "version": "1.0.0"
        }
    }


@router.put("/config")
async def update_config(config_data: dict):
    """
    更新系统配置
    """
    logger.info("更新系统配置")
    return {
        "success": True,
        "message": "配置更新成功"
    }
