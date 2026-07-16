"""
报价路由
Quotation Router
"""

import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.utils.logging_config import get_logger
from app.database import get_db


logger = get_logger("router.quotation")
router = APIRouter(prefix="/quotation", tags=["Quotation"])


@router.get("/", response_class=HTMLResponse, name="quotation.index")
async def index(request: Request):
    """
    报价列表页面
    """
    logger.info("访问报价列表页面")
    from main import app
    return app.state.templates.TemplateResponse(
        "quotation.html",
        {
            "request": request,
            "title": "报价",
        }
    )


@router.get("/create", response_class=HTMLResponse, name="quotation.create")
async def create(request: Request):
    """
    创建报价单页面
    """
    logger.info("访问创建报价单页面")
    from main import app
    return app.state.templates.TemplateResponse(
        "quotation.html",
        {
            "request": request,
            "title": "新建报价",
        }
    )


@router.get("/api/list", name="quotation.list")
async def list_quotations(
    page: int = 1,
    page_size: int = 20,
    status: str = None,
    db: Session = Depends(get_db)
):
    """
    获取报价列表 API
    """
    logger.info(f"获取报价列表: page={page}, page_size={page_size}")

    # TODO: 实现从数据库查询报价列表
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "total_pages": 0,
    }
