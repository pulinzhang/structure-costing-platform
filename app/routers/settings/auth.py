"""登录认证路由。"""

from fastapi import APIRouter, Depends, File, Header, Request, UploadFile
from sqlalchemy.orm import Session

from app.common.operation_log.context import set_request_user
from app.common.permissions.codes import Perm
from app.database import get_auxiliary_db, get_db
from app.deps.auth import extract_token, get_current_user, get_current_user_no_touch
from app.deps.permissions import require_perm
from app.schemas.dto.user_dto import (
    UserLoginDTO,
    UserSelfPasswordUpdateDTO,
    UserSelfUpdateDTO,
)
from app.schemas.vo.user_vo import AvatarUploadVO, LoginKeyVO, LoginVO, UserVO
from app.services.settings.users.auth import AuthService
from app.services.settings.users.service import UserService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/auth", tags=["登录认证"])
_auth_service = AuthService()
_user_service = UserService()


@router.get(
    "/login-key",
    response_model=ApiResponse[LoginKeyVO],
)
def login_key(
    request: Request,
    token_db: Session = Depends(get_auxiliary_db),
) -> ApiResponse[LoginKeyVO]:
    """签发一次性登录公钥。限流按连接地址，不读 X-Forwarded-For。"""
    peer = request.client.host if request.client else ""
    result = _auth_service.issue_login_key(token_db, peer)
    return ApiResponse.ok(data=result)


@router.post(
    "/login",
    response_model=ApiResponse[LoginVO],
)
def login(
    dto: UserLoginDTO,
    request: Request,
    db: Session = Depends(get_db),
    token_db: Session = Depends(get_auxiliary_db),
) -> ApiResponse[LoginVO]:
    """账号密码登录，返回 token（存入辅助库 user_tokens）"""
    result = _auth_service.login(db, token_db, dto)
    set_request_user(request, result.user)
    return ApiResponse.ok(data=result, message="登录成功")


@router.post(
    "/touch",
    response_model=ApiResponse[UserVO],
)
def touch(current_user: UserVO = Depends(get_current_user_no_touch)) -> ApiResponse[UserVO]:
    """心跳：校验 token 是否仍有效，不顺延空闲计时"""
    return ApiResponse.ok(data=current_user, message="会话有效")


@router.get(
    "/me",
    response_model=ApiResponse[UserVO],
)
def me(current_user: UserVO = Depends(get_current_user)) -> ApiResponse[UserVO]:
    """获取当前登录用户（主库最新资料）"""
    return ApiResponse.ok(data=current_user)


@router.put(
    "/me",
    response_model=ApiResponse[UserVO],
)
def update_me(
    dto: UserSelfUpdateDTO,
    db: Session = Depends(get_db),
    token_db: Session = Depends(get_auxiliary_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_PROFILE_UPDATE)),
) -> ApiResponse[UserVO]:
    """当前用户更新个人资料，并同步 token 快照"""
    user = _user_service.update_own_profile(db, current_user, dto)
    _auth_service.sync_profile_to_tokens(token_db, user)
    return ApiResponse.updated(data=user, message="资料已保存")


@router.post(
    "/avatar",
    response_model=ApiResponse[AvatarUploadVO],
)
async def upload_avatar(
    file: UploadFile = File(..., description="头像图片"),
    db: Session = Depends(get_db),
    token_db: Session = Depends(get_auxiliary_db),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_PROFILE_UPDATE)),
) -> ApiResponse[AvatarUploadVO]:
    """
    上传头像到 uploads/avatars/，写入用户 avatar，并返回相对路径 URL。
    例：/uploads/avatars/u1_20260812_103000_ab12cd34.png
    """
    content = await file.read()
    result = _auth_service.upload_own_avatar(
        db,
        token_db,
        current_user,
        file_content=content,
        filename=file.filename or "avatar.png",
    )
    return ApiResponse.ok(data=result, message=result.message)


@router.put(
    "/password",
    response_model=ApiResponse[UserVO],
)
def change_password(
    dto: UserSelfPasswordUpdateDTO,
    db: Session = Depends(get_db),
    token_db: Session = Depends(get_auxiliary_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_token: str | None = Header(default=None, alias="X-Token"),
    current_user: UserVO = Depends(require_perm(Perm.SETTINGS_PROFILE_PASSWORD)),
) -> ApiResponse[UserVO]:
    """当前用户修改密码：必须验证旧密码；默认注销其他设备"""
    user = _user_service.change_own_password(db, current_user, dto)
    if dto.logout_other_sessions:
        token = extract_token(authorization, x_token) or ""
        if token:
            _auth_service.logout_other_sessions(token_db, current_user.id, token)
    return ApiResponse.updated(data=user, message="密码已更新")


@router.post(
    "/logout",
    response_model=ApiResponse[None],
)
def logout(
    token_db: Session = Depends(get_auxiliary_db),
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_token: str | None = Header(default=None, alias="X-Token"),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[None]:
    """退出登录：删除服务端 token"""
    token = extract_token(authorization, x_token)
    _auth_service.logout(token_db, token or "")
    return ApiResponse.deleted(message="已退出登录")
