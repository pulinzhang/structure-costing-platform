"""
冲压工艺路由
前后端分离 API 接口
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import StampingPartService
from app.schemas.stamping import StampingPartQuery, StampingProcessUpdate
from app.utils.response import ApiResponse


router = APIRouter(prefix="/api/stamping", tags=["冲压工艺 API"])

_stamping_service = StampingPartService()


@router.get("/parts/list")
def list_parts(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
):
    """获取零件列表（包含工序）"""
    data, total, filter_options = _stamping_service.list_parts(db, query)
    return ApiResponse.list_(
        data=data,
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 个零件",
        filters=filter_options,
    )


@router.get("/parts/{part_id}")
def get_part(part_id: int, db: Session = Depends(get_db)):
    """获取单个零件（包含工序）"""
    part = _stamping_service.get_by_id(db, part_id)
    if not part:
        raise HTTPException(status_code=404, detail="零件不存在")
    return ApiResponse.success(data=part)


@router.delete("/parts/{part_id}")
def delete_part(part_id: int, db: Session = Depends(get_db)):
    """删除零件（同时删除关联工序）"""
    success = _stamping_service.delete(db, part_id)
    if not success:
        raise HTTPException(status_code=404, detail="零件不存在")
    return ApiResponse.deleted(message="零件删除成功")


@router.get("/parts")
def list_parts_legacy(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
):
    """获取零件列表（兼容旧路径）"""
    data, total, filter_options = _stamping_service.list_parts(db, query)
    return ApiResponse.list_(
        data=data,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filter_options,
    )


@router.patch("/processes/{process_id}")
def update_process(
    process_id: int,
    body: StampingProcessUpdate,
    db: Session = Depends(get_db),
):
    """更新工序（如成本系数）"""
    result = _stamping_service.update_process(db, process_id, body.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="工序不存在")
    return ApiResponse.success(data=result, message="工序更新成功")
