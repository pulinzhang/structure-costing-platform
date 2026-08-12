"""用户路由包"""

from app.routers.user.auth import router as auth_router
from app.routers.user.crud import router as user_crud_router

__all__ = ["auth_router", "user_crud_router"]
