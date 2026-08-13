# Stamping Routers Package

from app.routers.stamping.tonnage_price import router as tonnage_price_router
from app.routers.stamping.scrap_price import router as scrap_price_router

__all__ = ["tonnage_price_router", "scrap_price_router"]
