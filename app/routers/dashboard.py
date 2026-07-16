"""
仪表盘路由
Dashboard Router
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.utils.logging_config import get_logger


logger = get_logger("router.dashboard")
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    仪表盘首页
    显示系统概览和统计信息
    """
    logger.info("访问仪表盘首页")
    from main import app
    return app.state.templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "仪表盘",
        }
    )


# 直接绑定到根路径的路由
@router.get("", response_class=HTMLResponse)
async def dashboard_root(request: Request):
    """仪表盘根路由"""
    return await index(request)
