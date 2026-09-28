"""权限目录与用户授权路由。"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.common.operation_log.context import set_request_permission
from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_admin_user
from app.schemas.dto.user_permission_dto import UserPermissionsUpdateDTO
from app.schemas.vo.permission_vo import PermissionNodeVO
from app.schemas.vo.user_vo import UserVO
from app.services.settings.users.permission import PermissionService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/settings", tags=["权限管理"])
_permission_service = PermissionService()


@router.get(
    "/permissions/tree",
    response_model=ApiResponse[list[PermissionNodeVO]],
    summary="返回权限目录树（仅管理员）",
)
def get_permission_tree(
    current_user: UserVO = Depends(require_admin_user),
) -> ApiResponse[list[PermissionNodeVO]]:
    """返回权限目录树（仅管理员）"""
    tree = _permission_service.get_permission_tree(current_user)
    return ApiResponse.ok(data=tree, message="查询成功")


@router.get(
    "/users/{user_id:int}/permissions",
    response_model=ApiResponse[list[str]],
    summary="获取指定用户已授权权限码",
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
    "/users/{user_id:int}/permissions",
    response_model=ApiResponse[list[str]],
    summary="覆盖保存用户权限",
)
def set_user_permissions(
    user_id: int,
    dto: UserPermissionsUpdateDTO,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_admin_user),
) -> ApiResponse[list[str]]:
    """覆盖保存用户权限（强制合并个人资料必选码）"""
    set_request_permission(request, Perm.SETTINGS_USERS_GRANT)
    codes = _permission_service.set_user_permissions(db, user_id, dto.codes, current_user)
    return ApiResponse.updated(data=codes, message="授权已保存")
