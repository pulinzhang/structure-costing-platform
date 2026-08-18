"""
设置路由
Settings Router - API 接口
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.dto.settings_dto import SystemConfigUpdateDTO
from app.schemas.vo.settings_vo import ConfigVO
from app.schemas.vo.user_vo import UserVO
from app.services.settings.system.settings_service import SettingsService
from app.utils.logging_config import get_logger
from app.utils.response import ApiResponse


logger = get_logger("router.settings.system")
router = APIRouter(prefix="/api/settings/system", tags=["系统设置 API"])
_service = SettingsService()


@router.get("/config", response_model=ApiResponse[ConfigVO])
def get_config(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_SYSTEM_VIEW)),
) -> ApiResponse[ConfigVO]:
    """获取系统配置。"""
    logger.info("获取系统配置: user_id=%s", current_user.id)
    return ApiResponse.ok(data=_service.get_config(db), message="获取成功")


@router.put("/config", response_model=ApiResponse[ConfigVO])
def update_config(
    dto: SystemConfigUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_SYSTEM_UPDATE)),
) -> ApiResponse[ConfigVO]:
    """更新系统配置（应用名称、钢材密度）。"""
    logger.info("更新系统配置: user_id=%s", current_user.id)
    config = _service.update_config(db, dto, current_user=current_user)
    return ApiResponse.updated(data=config, message="配置更新成功")
