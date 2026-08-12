"""认证依赖：校验 token，返回当前用户。



设计约定：

- 除登录外，每个路由签名必须有 current_user: UserVO = Depends(get_current_user)

- 写操作：再以 current_user= 传给 Service

- 读/列表/删除：注入做鉴权即可，不必传给 Service

- Service 不读隐式上下文

"""



from __future__ import annotations



from fastapi import Depends, Header, HTTPException, status

from sqlalchemy.orm import Session



from app.database import get_auxiliary_db, get_db

from app.schemas.vo.user_vo import UserVO

from app.services.user.auth_service import AuthService



_auth_service = AuthService()





def extract_token(

    authorization: str | None = None,

    x_token: str | None = None,

) -> str | None:

    """优先 Authorization: Bearer xxx，其次 X-Token"""

    if authorization:

        parts = authorization.strip().split()

        if len(parts) == 2 and parts[0].lower() == "bearer":

            return parts[1].strip()

        if len(parts) == 1:

            return parts[0].strip()

    if x_token:

        return x_token.strip()

    return None





def get_current_user(

    db: Session = Depends(get_db),

    token_db: Session = Depends(get_auxiliary_db),

    authorization: str | None = Header(default=None, alias="Authorization"),

    x_token: str | None = Header(default=None, alias="X-Token"),

) -> UserVO:

    """强制登录：校验 token 并顺延活动时间，返回 UserVO。"""

    token = extract_token(authorization, x_token)

    try:

        return _auth_service.get_user_by_token(db, token_db, token or "", do_touch=True)

    except PermissionError as exc:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail=str(exc),

        ) from exc

