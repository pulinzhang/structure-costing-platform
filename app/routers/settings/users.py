"""用户 CRUD 路由"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_auxiliary_db, get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.user_dto import (
    UserCreateDTO,
    UserPasswordUpdateDTO,
    UserQueryDTO,
    UserUpdateDTO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.settings.users.auth_service import AuthService
from app.services.settings.users.user_service import UserService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/settings/users", tags=["用户管理"])
_user_service = UserService()
_auth_service = AuthService()


@router.get(
    "",
    response_model=ApiResponse[PageResult[UserVO]],
)
def list_users(
    query: UserQueryDTO = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_USERS_VIEW)),
) -> ApiResponse[PageResult[UserVO]]:
    """分页查询用户"""
    rows, total, filters = _user_service.paginate(db, query)
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filters,
        message="查询成功",
    )


@router.get(
    "/all",
    response_model=ApiResponse[list[UserVO]],
)
def list_all_users(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_USERS_VIEW)),
) -> ApiResponse[list[UserVO]]:
    """获取全部用户（不分页）"""
    users = _user_service.list_users(db)
    return ApiResponse.ok(data=users, message="查询成功")


@router.get(
    "/{user_id:int}",
    response_model=ApiResponse[UserVO],
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_USERS_VIEW)),
) -> ApiResponse[UserVO]:
    """获取单个用户"""
    user = _user_service.get_by_id(db, user_id)
    return ApiResponse.ok(data=user)


@router.post(
    "",
    response_model=ApiResponse[UserVO],
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    dto: UserCreateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_USERS_CREATE)),
) -> ApiResponse[UserVO]:
    """创建用户"""
    user = _user_service.create(db, dto, current_user=current_user)
    return ApiResponse.created(data=user, message="创建成功")


@router.put(
    "/{user_id:int}",
    response_model=ApiResponse[UserVO],
)
def update_user(
    user_id: int,
    dto: UserUpdateDTO,
    db: Session = Depends(get_db),
    token_db: Session = Depends(get_auxiliary_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_USERS_UPDATE)),
) -> ApiResponse[UserVO]:
    """更新用户资料；若停用账号则立即作废其全部登录会话"""
    payload = dto.model_dump(exclude_unset=True)
    user = _user_service.update(db, user_id, dto, current_user=current_user)

    # 管理员停用 → 拒绝继续使用系统（踢下线）
    if payload.get("is_active") is False:
        _auth_service.revoke_all_sessions(token_db, user.id)

    return ApiResponse.updated(data=user, message="更新成功")


@router.put(
    "/{user_id:int}/password",
    response_model=ApiResponse[UserVO],
)
def update_password(
    user_id: int,
    dto: UserPasswordUpdateDTO,
    db: Session = Depends(get_db),
    token_db: Session = Depends(get_auxiliary_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_USERS_PASSWORD)),
) -> ApiResponse[UserVO]:
    """管理员重置密码：改密后作废该用户全部会话，强制重新登录"""
    user = _user_service.update_password(db, user_id, dto, current_user=current_user)
    _auth_service.revoke_all_sessions(token_db, user.id)
    return ApiResponse.updated(data=user, message="密码已更新")


@router.delete(
    "/{user_id:int}",
    response_model=ApiResponse[None],
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    token_db: Session = Depends(get_auxiliary_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_USERS_DELETE)),
) -> ApiResponse[None]:
    """删除用户并作废其登录会话"""
    _user_service.delete(db, user_id, current_user=current_user)
    _auth_service.revoke_all_sessions(token_db, user_id)
    return ApiResponse.deleted(message="删除成功")
