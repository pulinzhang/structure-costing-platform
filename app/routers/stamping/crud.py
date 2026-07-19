"""
冲压工艺路由
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import StampingPartService
from app.schemas.stamping import StampingPartQuery
from app.utils.response import ApiResponse


router = APIRouter(prefix="/stamping", tags=["Stamping"])

_stamping_service = StampingPartService()


@router.get("/", name="stamping.index")
def stamping_index():
    """冲压工艺首页 - 重定向到零件列表"""
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/stamping/parts", status_code=302)


@router.get("/parts/page", name="stamping.parts", response_class=HTMLResponse)
async def list_parts_page(request: Request):
    """冲压零件列表页面"""
    return request.app.state.templates.TemplateResponse("stamping/parts.html", {"request": request})


@router.get("/parts/list", name="stamping.parts.list")
def list_parts(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
):
    """获取零件列表（包含工序）"""
    page = query.skip // query.limit + 1 if query.limit > 0 else 1
    data, total = _stamping_service.list_parts(db, query)
    return ApiResponse.list_(
        data=data,
        total=total,
        page=page,
        page_size=query.limit,
        message=f"查询到 {total} 个零件",
    )


@router.get("/parts/{part_id}", name="stamping.parts.get")
def get_part(part_id: int, db: Session = Depends(get_db)):
    """获取单个零件（包含工序）"""
    part = _stamping_service.get_by_id(db, part_id)
    if not part:
        raise HTTPException(status_code=404, detail="零件不存在")
    return ApiResponse.success(data=part)


@router.delete("/parts/{part_id}", name="stamping.parts.delete")
def delete_part(part_id: int, db: Session = Depends(get_db)):
    """删除零件（同时删除关联工序）"""
    success = _stamping_service.delete(db, part_id)
    if not success:
        raise HTTPException(status_code=404, detail="零件不存在")
    return ApiResponse.deleted(message="零件删除成功")
