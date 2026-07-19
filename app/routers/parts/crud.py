"""
零件路由
Parts Router
"""

import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.utils.logging_config import get_logger
from app.database import get_db
from app.utils.response import ApiResponse


logger = get_logger("router.parts")
router = APIRouter(prefix="/parts", tags=["Parts"])


@router.get("/", response_class=HTMLResponse, name="parts.index")
async def index(request: Request):
    """
    零件列表页面
    """
    logger.info("访问零件列表页面")
    return request.app.state.templates.TemplateResponse(
        "parts.html",
        {
            "request": request,
            "title": "零件",
        }
    )


@router.get("/api/list", name="parts.list")
async def list_parts(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    db: Session = Depends(get_db)
):
    """
    获取零件列表 API
    """
    logger.info(f"获取零件列表: page={page}, page_size={page_size}")

    # TODO: 实现从数据库查询零件列表
    return ApiResponse.list_(
        data=[],
        total=0,
        message="零件列表功能开发中"
    )
