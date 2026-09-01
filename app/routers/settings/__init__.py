"""设置路由切片"""

from app.routers.settings.auth.crud import router as auth_router
from app.routers.settings.logs.crud import router as logs_router
from app.routers.settings.system.crud import router as system_router
from app.routers.settings.users.crud import router as users_router
from app.routers.settings.users.permissions import router as permissions_router

__all__ = [
    "auth_router",
    "logs_router",
    "permissions_router",
    "system_router",
    "users_router",
]
