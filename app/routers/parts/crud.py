"""
零件路由
Parts Router - API 接口
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.utils.logging_config import get_logger
from app.database import get_db
from app.utils.response import ApiResponse
from app.schemas.stamping import StampingPartQuery
from app.services.stamping.stamping_service import StampingPartService


logger = get_logger("router.parts")
router = APIRouter(prefix="/api/parts", tags=["零件 API"])


@router.get("/list")
async def list_parts(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=500, description="每页条数"),
    vehicle_model: str = Query(None, description="车型筛选"),
    version: str = Query(None, description="版本筛选"),
    part_number: str = Query(None, description="零件号搜索"),
    part_name: str = Query(None, description="零件名称搜索"),
    db: Session = Depends(get_db)
):
    """
    获取零件列表 API
    """
    logger.info(f"获取零件列表: page={page}, page_size={page_size}")

    query = StampingPartQuery(
        page=page,
        size=page_size,
        vehicle_model=vehicle_model,
        version=version,
        part_number=part_number,
        part_name=part_name,
    )

    service = StampingPartService()
    data, total = service.list_parts(db, query)

    return ApiResponse.list_(data=data, total=total)
