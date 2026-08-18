"""冲压零件价格核算 Router 包。"""

from app.routers.costing.stamping_part_cost.calc import router as calc_router
from app.routers.costing.stamping_part_cost.crud import router as crud_router

__all__ = ["calc_router", "crud_router"]
