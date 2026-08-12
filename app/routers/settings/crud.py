"""
设置路由
Settings Router - API 接口
"""

from fastapi import APIRouter, Body, Depends

from app.utils.logging_config import get_logger
from app.deps.auth import get_current_user
from app.schemas.vo.settings_vo import ConfigVO
from app.schemas.vo.user_vo import UserVO
from app.utils.response import ApiResponse


logger = get_logger("router.settings")
router = APIRouter(prefix="/api/settings", tags=["系统设置 API"])


@router.get("/config", response_model=ApiResponse[ConfigVO])
async def get_config(
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[ConfigVO]:
    """
    获取系统配置
    """
    logger.info("获取系统配置")
    return ApiResponse.ok(
        data=ConfigVO(
            app_name="汽车冲压件自动核价平台",
            version="1.0.0"
        ),
        message="获取成功"
    )


@router.put("/config", response_model=ApiResponse[None])
async def update_config(
    config_data: ConfigVO = Body(...),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[None]:
    """
    更新系统配置
    """
    logger.info("更新系统配置")
    return ApiResponse.updated(data=None, message="配置更新成功")
