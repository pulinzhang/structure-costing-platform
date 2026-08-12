"""
冲压工艺路由
前后端分离 API 接口
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps.auth import get_current_user
from app.common.permissions.checks import require_permission
from app.services import StampingPartService
from app.schemas.vo.stamping_vo import (
    StampingPartQuery,
    StampingPartWithProcessesResponse,
    StampingProcessUpdate,
    StampingProcessItemUpdate,
    StampingPartListResponse,
    StampingProcessResponse,
    StampingMaterialQuery,
    StampingMaterialResponse,
    StampingCascadeFilterQuery,
    StampingCascadeFilterOptionsVO,
)
from app.schemas.vo.user_vo import UserVO
from app.utils.response import ApiResponse
from app.schemas.common.page_result import PageResult


class BatchUpdateResponse(BaseModel):
    """批量更新响应 VO"""
    updated: int


router = APIRouter(prefix="/api/stamping", tags=["冲压工艺 API"])

_stamping_service = StampingPartService()

@router.get("/parts/list", response_model=ApiResponse[PageResult[StampingPartListResponse]])
def list_parts(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[PageResult[StampingPartListResponse]]:
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
def get_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[StampingPartWithProcessesResponse]:
    """获取单个零件（包含工序）"""
    vo = _stamping_service.get_by_id(db, part_id)
    if not vo:
        raise HTTPException(status_code=404, detail="零件不存在")
    return ApiResponse.ok(data=vo, message="获取零件成功")


@router.delete("/parts/{part_id}", response_model=ApiResponse[None])
def delete_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[None]:
    """删除零件（同时删除关联工序）"""
    require_permission(current_user, "op:stamping-parts:delete")
    _stamping_service.delete(db, part_id)
    return ApiResponse.deleted(message="零件删除成功")


@router.get("/parts", response_model=ApiResponse[PageResult[StampingPartListResponse]])
def list_parts_legacy(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[PageResult[StampingPartListResponse]]:
    """获取零件列表（兼容旧路径）"""
    data, total, filter_options = _stamping_service.list_parts(db, query)
    return ApiResponse.list_(
        items=data,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filter_options,
    )


@router.get("/materials", response_model=ApiResponse[PageResult[StampingMaterialResponse]])
def list_materials(
    query: StampingMaterialQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[PageResult[StampingMaterialResponse]]:
    """获取材料列表（material, thickness, sheet_length, sheet_width）"""
    data, total, filter_options = _stamping_service.list_materials(db, query)
    return ApiResponse.list_(
        items=data,
        total=total,
        page=query.page,
        page_size=query.size,
        filters=filter_options,
    )


@router.get(
    "/filters/cascade",
    response_model=ApiResponse[StampingCascadeFilterOptionsVO],
)
def get_cascade_filters(
    query: StampingCascadeFilterQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[StampingCascadeFilterOptionsVO]:
    """
    冲压级联筛选选项：基地 → 冲压工厂 → 配套车型
    """
    options = _stamping_service.get_cascade_filter_options(db, query)
    return ApiResponse.ok(data=options, message="获取成功")


@router.patch("/processes/{process_id}", response_model=ApiResponse[StampingProcessResponse])
def update_process(
    process_id: int,
    body: StampingProcessUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[StampingProcessResponse]:
    """更新工序（如成本系数）"""
    result = _stamping_service.update_process(
        db, process_id, body.model_dump(exclude_unset=True), current_user=current_user
    )
    if not result:
        raise HTTPException(status_code=404, detail="工序不存在")
    return ApiResponse.ok(data=result, message="工序更新成功")


@router.put("/parts/{part_id}/processes", response_model=ApiResponse[BatchUpdateResponse])
def batch_update_processes(
    part_id: int,
    body: List[StampingProcessItemUpdate],
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(get_current_user),
) -> ApiResponse[BatchUpdateResponse]:
    """批量更新零件的所有工序（仅更新 cost_ratio）"""
    require_permission(current_user, "op:stamping-parts:update")
    updated = _stamping_service.batch_update_processes(
        db, [item.model_dump() for item in body], current_user=current_user
    )
    return ApiResponse.ok(
        data=BatchUpdateResponse(updated=updated),
        message=f"成功更新 {updated} 条工序",
    )
