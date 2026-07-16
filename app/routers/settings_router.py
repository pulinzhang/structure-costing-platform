"""
设置路由
Settings Router
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.utils.logging_config import get_logger


logger = get_logger("router.settings")
router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/", response_class=HTMLResponse, name="settings.index")
async def index(request: Request):
    """
    设置页面
    """
    logger.info("访问设置页面")
    from main import app
    return app.state.templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "title": "设置",
        }
    )


@router.get("/general", response_class=HTMLResponse, name="settings.general")
async def general(request: Request):
    """基本设置页面"""
    return await index(request)


@router.get("/costing", response_class=HTMLResponse, name="settings.costing")
async def costing_settings(request: Request):
    """核价参数设置页面"""
    return await index(request)
