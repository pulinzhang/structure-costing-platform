"""
核价路由
Costing Router
"""

import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.utils.logging_config import get_logger
from app.database import get_db


logger = get_logger("router.costing")
router = APIRouter(prefix="/costing", tags=["Costing"])


@router.get("/", response_class=HTMLResponse, name="costing.index")
async def index(request: Request):
    """
    核价页面
    """
    logger.info("访问核价页面")
    from main import app
    return app.state.templates.TemplateResponse(
        "costing.html",
        {
            "request": request,
            "title": "核价",
        }
    )


@router.get("/start", response_class=HTMLResponse, name="costing.start")
async def start_costing(request: Request):
    """
    开始核价页面
    """
    logger.info("访问开始核价页面")
    from main import app
    return app.state.templates.TemplateResponse(
        "costing.html",
        {
            "request": request,
            "title": "核价",
        }
    )


@router.post("/api/calculate", name="costing.calculate")
async def calculate_cost(
    part_ids: list[int],
    db: Session = Depends(get_db)
):
    """
    计算成本 API
    """
    logger.info(f"计算成本: {len(part_ids)} 个零件")

    # TODO: 实现成本计算逻辑
    return {
        "success": True,
        "results": [],
    }
