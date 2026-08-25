"""
成品月核价 — 计算 API（异步）
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.l0_assembly_cost_dto import L0AssemblyCostCalcDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.l0_assembly_cost_vo import (
    L0AssemblyCostCalcLogVO,
    L0AssemblyCostCalcReadyVO,
    L0AssemblyCostCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_PENDING,
    TASK_TYPE_L0_ASSEMBLY_COST_CALC,
    AsyncTaskService,
)
from app.services.costing.l0_assembly_cost.l0_assembly_cost_service import (
    L0AssemblyCostService,
)
from app.utils.response import ApiResponse

router = APIRouter(
    prefix="/api/costing/l0-assembly-costs",
    tags=["成品核价计算"],
)

_service = L0AssemblyCostService()
_async_task_service = AsyncTaskService()


@router.get(
    "/filters/years",
    response_model=ApiResponse[List[int]],
)
def list_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.L0_ASSEMBLY_COST_VIEW,
            Perm.L0_ASSEMBLY_COST_CALC_VIEW,
        )
    ),
) -> ApiResponse[List[int]]:
    """上游可核算年度（冲压价/年度价/焊接费/包装运输并集），非结果表年份。"""
    years = _service.list_years(db)
    return ApiResponse.ok(data=years)


@router.get(
    "/calc/ready",
    response_model=ApiResponse[L0AssemblyCostCalcReadyVO],
)
def get_calc_ready(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    location: str = Query(...),
    vehicle_model: str = Query(...),
    bom_version: str = Query(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_CALC_VIEW)),
) -> ApiResponse[L0AssemblyCostCalcReadyVO]:
    data = _service.get_calc_ready(
        db,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
    )
    return ApiResponse.ok(data=data)


@router.get(
    "/calc/logs",
    response_model=ApiResponse[PageResult[L0AssemblyCostCalcLogVO]],
)
def list_calc_logs(
    year: int | None = Query(None),
    month: int | None = Query(None),
    location: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    bom_version: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_CALC_VIEW)),
) -> ApiResponse[PageResult[L0AssemblyCostCalcLogVO]]:
    rows, total = _service.list_calc_logs(
        db,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        page=page,
        size=size,
    )
    return ApiResponse.list_(
        items=rows,
        total=total,
        page=page,
        page_size=size,
        message=f"查询到 {total} 条计算历史",
    )


@router.get(
    "/calc/logs/{log_id}",
    response_model=ApiResponse[L0AssemblyCostCalcLogVO],
)
def get_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_CALC_VIEW)),
) -> ApiResponse[L0AssemblyCostCalcLogVO]:
    record = _service.get_calc_log(db, log_id)
    return ApiResponse.ok(data=record)


@router.delete(
    "/calc/logs/{log_id}",
    response_model=ApiResponse[None],
)
def delete_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_CALC_DELETE)),
) -> ApiResponse[None]:
    _service.delete_calc_log(db, log_id)
    return ApiResponse.deleted(message="计算日志已删除")


@router.get(
    "/calc/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_calc_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_CALC_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    task = _async_task_service.require_snapshot(
        task_id, TASK_TYPE_L0_ASSEMBLY_COST_CALC
    )
    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = (
        L0AssemblyCostCalcResultVO.model_validate(result_raw)
        if result_raw
        else None
    )
    return ApiResponse.ok(
        data=AsyncTaskProgressVO.from_snapshot(
            task,
            default_status=STATUS_PENDING,
            result=result,
        ),
    )


@router.post(
    "/calc",
    response_model=ApiResponse[AsyncTaskAcceptedVO],
)
def calculate(
    dto: L0AssemblyCostCalcDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.L0_ASSEMBLY_COST_CALC_RUN)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    accepted = _service.start_calc(db, dto, current_user=current_user)

    return ApiResponse.ok(
        data=accepted,
        message="已提交后台计算",
    )
