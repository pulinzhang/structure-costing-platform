"""核价路由切片"""

from app.routers.costing.engine.crud import router as engine_router
from app.routers.costing.steel_price.calc import router as steel_price_calc_router
from app.routers.costing.steel_price.crud import router as steel_price_router
from app.routers.costing.stamping_part_cost.crud import router as stamping_part_cost_router

__all__ = [
    "engine_router",
    "steel_price_calc_router",
    "steel_price_router",
    "stamping_part_cost_router",
]
