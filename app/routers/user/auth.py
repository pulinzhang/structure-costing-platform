"""登录认证路由"""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_auxiliary_db, get_db
from app.deps.auth import extract_token, get_current_user
from app.schemas.dto.user_dto import UserLoginDTO
from app.schemas.vo.user_vo import LoginVO, UserVO
from app.services.user.auth_service import AuthService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/auth", tags=["登录认证"])
_auth_service = AuthService()


@router.post(
    "/login",
    response_model=ApiResponse[LoginVO],
)
def login(
    dto: UserLoginDTO,
    db: Session = Depends(get_db),
    token_db: Session = Depends(get_auxiliary_db),
) -> ApiResponse[LoginVO]:
    """账号密码登录，返回 token（存入辅助库 user_tokens）"""
    try:
        result = _auth_service.login(db, token_db, dto)
        return ApiResponse.ok(data=result, message="登录成功")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@router.post(
    "/touch",
    response_model=ApiResponse[UserVO],
)
def touch(current_user: UserVO = Depends(get_current_user)) -> ApiResponse[UserVO]:
    """心跳：校验并顺延 token（复用 get_current_user）"""
    return ApiResponse.ok(data=current_user, message="已续期")


@router.get(
    "/me",
    response_model=ApiResponse[UserVO],
)
def me(current_user: UserVO = Depends(get_current_user)) -> ApiResponse[UserVO]:
    """获取当前登录用户（顺带续期）"""
    return ApiResponse.ok(data=current_user)


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
