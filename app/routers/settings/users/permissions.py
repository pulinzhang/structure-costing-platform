"""权限目录与用户授权路由"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps.permissions import require_admin_user
from app.database import get_db
from app.schemas.dto.user_permission_dto import UserPermissionsUpdateDTO
from app.schemas.vo.permission_vo import PermissionNodeVO
from app.schemas.vo.user_vo import UserVO
from app.services.settings.users.permission_service import PermissionService
from app.utils.response import ApiResponse

router = APIRouter(tags=["权限管理"])
_permission_service = PermissionService()


@router.get(
    "/api/settings/permissions/tree",
    response_model=ApiResponse[list[PermissionNodeVO]],
)
def get_permission_tree(
    current_user: UserVO = Depends(require_admin_user),
) -> ApiResponse[list[PermissionNodeVO]]:
    """返回权限目录树（仅管理员）"""
    tree = _permission_service.get_permission_tree(current_user)
    nodes = [PermissionNodeVO.model_validate(n) for n in tree]
    return ApiResponse.ok(data=nodes, message="查询成功")


@router.get(
    "/api/settings/users/{user_id}/permissions",
    response_model=ApiResponse[list[str]],
)
def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_admin_user),
) -> ApiResponse[list[str]]:
    """获取指定用户已授权权限码"""
    codes = _permission_service.get_user_permission_codes(db, user_id, current_user)
    return ApiResponse.ok(data=codes, message="查询成功")


@router.put(
    "/api/settings/users/{user_id}/permissions",
    response_model=ApiResponse[list[str]],
)
def set_user_permissions(
    user_id: int,
    dto: UserPermissionsUpdateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_admin_user),
) -> ApiResponse[list[str]]:
    """覆盖保存用户权限（强制合并个人资料必选码）"""
    codes = _permission_service.set_user_permissions(db, user_id, dto.codes, current_user)
    return ApiResponse.updated(data=codes, message="授权已保存")
