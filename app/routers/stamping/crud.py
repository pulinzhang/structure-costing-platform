"""
冲压工艺路由
前后端分离 API 接口
"""

from typing import List
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.services.stamping.stamping_part_export_service import StampingPartExportService
from app.services.stamping.stamping_service import StampingPartService
from app.schemas.dto.stamping_part_dto import StampingPartBatchDeleteDTO
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
    StampingPartBatchDeleteResultVO,
    BatchUpdateResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.utils.response import ApiResponse
from app.schemas.common.page_result import PageResult


router = APIRouter(prefix="/api/stamping", tags=["冲压工艺 API"])

_stamping_service = StampingPartService()
_export_service = StampingPartExportService()


@router.get("/parts/list", response_model=ApiResponse[PageResult[StampingPartListResponse]])
def list_parts(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_VIEW)),
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


@router.get("/parts/export-download")
def export_download(
    location: str = Query(..., min_length=1, description="采购基地"),
    stamping_supplier: str = Query(..., min_length=1, description="冲压工厂"),
    vehicle_model: str = Query(..., min_length=1, description="车型"),
    version: str = Query(..., min_length=1, description="版本"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_EXPORT)),
) -> StreamingResponse:
    """按基地 + 冲压工厂 + 车型 + 版本导出工艺确认表（与导入同范围，多费用比例列）。"""
    content, filename = _export_service.export(
        db,
        location=location,
        stamping_supplier=stamping_supplier,
        vehicle_model=vehicle_model,
        version=version,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post(
    "/parts/batch-delete",
    response_model=ApiResponse[StampingPartBatchDeleteResultVO],
)
def batch_delete_parts(
    body: StampingPartBatchDeleteDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_DELETE)),
) -> ApiResponse[StampingPartBatchDeleteResultVO]:
    """按基地 + 冲压工厂 + 车型 + 版本批量删除零件（四者同时必填）。"""
    result = _stamping_service.batch_delete(db, body)
    scope = (
        f"{result.location} / {result.stamping_supplier} / "
        f"{result.vehicle_model} / {result.version}"
    )
    return ApiResponse.ok(
        data=result,
        message=f"已删除 {result.deleted_count} 个零件（{scope}）",
    )


@router.get("/parts/{part_id}", response_model=ApiResponse[StampingPartWithProcessesResponse])
def get_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_VIEW)),
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
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_DELETE)),
) -> ApiResponse[None]:
    """删除零件（同时删除关联工序）"""
    _stamping_service.delete(db, part_id)
    return ApiResponse.deleted(message="零件删除成功")


@router.get("/parts", response_model=ApiResponse[PageResult[StampingPartListResponse]])
def list_parts_legacy(
    query: StampingPartQuery = Depends(),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_VIEW)),
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
    current_user: UserVO = Depends(
        require_any_perm(Perm.STAMPING_PARTS_VIEW, Perm.STEEL_PRICE_CALC_VIEW)
    ),
) -> ApiResponse[PageResult[StampingMaterialResponse]]:
    """获取材料列表（material, thickness, sheet_length, sheet_width；拼焊件为子片拼接）"""
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
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STAMPING_PARTS_VIEW,
            Perm.STEEL_PRICE_CALC_VIEW,
            Perm.STEEL_PRICE_LIST_VIEW,
            Perm.STAMPING_PROCESS_FEE_CALC_VIEW,
            Perm.STAMPING_PROCESS_FEE_VIEW,
        )
    ),
) -> ApiResponse[StampingCascadeFilterOptionsVO]:
    """冲压级联筛选选项：基地 → 冲压工厂 → 配套车型"""
    options = _stamping_service.get_cascade_filter_options(db, query)
    return ApiResponse.ok(data=options, message="获取成功")


@router.patch("/processes/{process_id}", response_model=ApiResponse[StampingProcessResponse])
def update_process(
    process_id: int,
    body: StampingProcessUpdate,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_UPDATE)),
) -> ApiResponse[StampingProcessResponse]:
    """更新工序（如成本系数）"""
    result = _stamping_service.update_process(
        db, process_id, body, current_user=current_user
    )
    if not result:
        raise HTTPException(status_code=404, detail="工序不存在")
    return ApiResponse.ok(data=result, message="工序更新成功")


@router.put("/parts/{part_id}/processes", response_model=ApiResponse[BatchUpdateResponse])
def batch_update_processes(
    part_id: int,
    body: List[StampingProcessItemUpdate],
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PARTS_UPDATE)),
) -> ApiResponse[BatchUpdateResponse]:
    """批量更新零件的所有工序（仅更新 cost_ratio）"""
    updated = _stamping_service.batch_update_processes(
        db, body, current_user=current_user
    )
    return ApiResponse.ok(
        data=BatchUpdateResponse(updated=updated),
        message=f"成功更新 {updated} 条工序",
    )
