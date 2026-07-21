"""
核价路由
Costing Router - API 接口
"""

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from app.utils.logging_config import get_logger
from app.database import get_db
from app.utils.response import ApiResponse


logger = get_logger("router.costing")
router = APIRouter(prefix="/api/costing", tags=["核价 API"])


@router.post("/calculate")
async def calculate_cost(
    part_ids: list[int] = Body(..., description="零件ID列表"),
    db: Session = Depends(get_db)
):
    """
    计算成本 API
    """
    logger.info(f"计算成本: {len(part_ids)} 个零件")

    # TODO: 核价功能开发中，返回占位数据
    return ApiResponse.success(
        data={"results": [], "part_count": len(part_ids)},
        message="成本计算功能开发中"
    )
