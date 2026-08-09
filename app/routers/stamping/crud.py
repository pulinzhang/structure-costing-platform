"""
冲压工艺路由
前后端分离 API 接口
"""

from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import StampingPartService
from app.schemas.vo.stamping_vo import (
    StampingPartQuery,
    StampingPartWithProcessesResponse,
    StampingProcessUpdate,
    StampingProcessItemUpdate,
    StampingPartListResponse,
    StampingProcessResponse,
)
from app.utils.response import ApiResponse
from app.schemas.common.page_result import PageResult
from app.exceptions import NotFoundException

class BatchUpdateResponse(BaseModel):
    """批量更新响应 VO"""
    updated: int


router = APIRouter(prefix="/api/stamping", tags=["冲压工艺 API"])

_stamping_service = StampingPartService()


@router.get("/parts/list", response_model=ApiResponse[PageResult[StampingPartListResponse]])
def list_parts(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
):
    """获取零件列表（包含工序）"""
    data, total, filter_options = _stamping_service.list_parts(db, query)
    return ApiResponse.list_(
        items=data,
        total=total,
        page=query.page,
        page_size=query.size,
        message=f"查询到 {total} 个零件",
        filters=filter_options,
    )


@router.get("/parts/{part_id}", response_model=ApiResponse[StampingPartWithProcessesResponse])
def get_part(part_id: int, db: Session = Depends(get_db)):
    """获取单个零件（包含工序）"""
    vo = _stamping_service.get_by_id(db, part_id)
    if not vo:
        raise NotFoundException(f"零件不存在: id={part_id}")
    return ApiResponse.ok(data=vo, message="获取零件成功")


@router.delete("/parts/{part_id}", response_model=ApiResponse[None])
def delete_part(part_id: int, db: Session = Depends(get_db)):
    """删除零件（同时删除关联工序）"""
    _stamping_service.delete(db, part_id)
    return ApiResponse.deleted(message="零件删除成功")


@router.get("/parts", response_model=ApiResponse[PageResult[StampingPartListResponse]])
def list_parts_legacy(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
):
    """获取零件列表（兼容旧路径）"""
    data, total, filter_options = _stamping_service.list_parts(db, query)
    return ApiResponse.list_(
        items=data,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filter_options,
    )


@router.patch("/processes/{process_id}", response_model=ApiResponse[StampingProcessResponse])
def update_process(
    process_id: int,
    body: StampingProcessUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse[StampingProcessResponse]:
    """更新工序（如成本系数）"""
    result = _stamping_service.update_process(db, process_id, body.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="工序不存在")
    return ApiResponse.success(data=result, message="工序更新成功")


@router.put("/parts/{part_id}/processes", response_model=ApiResponse[BatchUpdateResponse])
def batch_update_processes(
    part_id: int,
    body: List[StampingProcessItemUpdate],
    db: Session = Depends(get_db),
) -> ApiResponse[BatchUpdateResponse]:
    """批量更新零件的所有工序（仅更新 cost_ratio）"""
    updated = _stamping_service.batch_update_processes(
        db, [item.model_dump() for item in body]
    )
    return ApiResponse.success(data=BatchUpdateResponse(updated=updated), message=f"成功更新 {updated} 条工序")
