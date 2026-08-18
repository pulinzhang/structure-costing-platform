"""用户与权限路由包"""

from app.routers.settings.users.crud import router as users_router
from app.routers.settings.users.permissions import router as permissions_router

__all__ = ["users_router", "permissions_router"]
