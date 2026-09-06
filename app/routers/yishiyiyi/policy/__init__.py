"""钢价政策路由"""

from app.routers.yishiyiyi.policy.crud import router as crud_router
from app.routers.yishiyiyi.policy.export import router as export_router
from app.routers.yishiyiyi.policy.upload import router as upload_router

__all__ = ["crud_router", "export_router", "upload_router"]
