"""
报价路由
Quotation Router - API 接口
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.utils.logging_config import get_logger
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.vo.user_vo import UserVO
from app.utils.response import ApiResponse


logger = get_logger("router.quotation")
router = APIRouter(prefix="/api/quotation", tags=["报价 API"])

# 默认分页大小常量
DEFAULT_PAGE_SIZE = 20


@router.get("/list")
async def list_quotations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=500, description="每页条数"),
    status: str = Query(None, description="状态筛选"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.QUOTATION_VIEW)),
):
    """
    获取报价列表 API
    """
    logger.info(f"获取报价列表: page={page}, page_size={page_size}, status={status}")

    # TODO: 报价功能开发中，返回占位数据
    return ApiResponse.list_(
        items=[],
        total=0,
        page=page,
        page_size=page_size,
        message="报价列表功能开发中",
    )
