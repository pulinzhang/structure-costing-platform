# Stamping Router Package

from app.routers.stamping.crud import router as crud_router
from app.routers.stamping.upload import router as upload_router

__all__ = ["crud_router", "upload_router"]
