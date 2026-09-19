"""
成品月核价 — 计算 API（异步）
"""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common import DeletedCountVO, PageResult
from app.schemas.dto.assembly_cost_dto import AssemblyCostCalcDTO
from app.schemas.vo.assembly_cost_vo import (
    AssemblyCostCalcLogVO,
    AssemblyCostCalcReadyVO,
    AssemblyCostCalcResultVO,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_PENDING,
    TASK_TYPE_ASSEMBLY_COST_CALC,
    AsyncTaskService,
)
from app.services.costing.assembly_cost.assembly_cost_service import (
    AssemblyCostService,
)
from app.services.costing.assembly_cost.calc_report.report_export_service import (
    AssemblyCostCalcReportExportService,
)
from app.utils.response import ApiResponse

router = APIRouter(
    prefix="/api/costing/assembly-costs",
    tags=["总成核价计算"],
)

_service = AssemblyCostService()
_async_task_service = AsyncTaskService()
_report_export_service = AssemblyCostCalcReportExportService()


@router.get(
    "/filters/years",
    response_model=ApiResponse[list[int]],
)
def list_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.ASSEMBLY_COST_VIEW,
            Perm.ASSEMBLY_COST_CALC_VIEW,
        )
    ),
) -> ApiResponse[list[int]]:
    """上游可核算年度（冲压价/年度价/焊接费/包装运输并集），非结果表年份。"""
    years = _service.list_years(db)
    return ApiResponse.ok(data=years)


@router.get(
    "/calc/ready",
    response_model=ApiResponse[AssemblyCostCalcReadyVO],
)
def get_calc_ready(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    location: str = Query(...),
    vehicle_model: str = Query(...),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_CALC_VIEW)),
) -> ApiResponse[AssemblyCostCalcReadyVO]:
    data = _service.get_calc_ready(
        db,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
    )
    return ApiResponse.ok(data=data)


@router.get(
    "/calc/logs",
    response_model=ApiResponse[PageResult[AssemblyCostCalcLogVO]],
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
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_CALC_VIEW)),
) -> ApiResponse[PageResult[AssemblyCostCalcLogVO]]:
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
    "/calc/logs/{log_id:int}",
    response_model=ApiResponse[AssemblyCostCalcLogVO],
)
def get_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_CALC_VIEW)),
) -> ApiResponse[AssemblyCostCalcLogVO]:
    record = _service.get_calc_log(db, log_id)
    return ApiResponse.ok(data=record)


@router.get("/calc/logs/{log_id:int}/export-download")
def export_calc_report(
    log_id: int,
    keyword: str | None = Query(None, description="零件号、名称、说明"),
    status: str | None = Query(None, description="卡状态：ok/partial/failed/skipped"),
    level: int | None = Query(None, ge=0, le=20, description="层级"),
    tree_root: Literal["all", "yes", "no"] = Query("all", description="树根筛选"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_CALC_VIEW)),
) -> StreamingResponse:
    """导出本条计算日志的浅色报告 Excel（当前筛选口径）。"""
    status_value = status.strip() if status else None
    if status_value in {"", "all"}:
        status_value = None
    content, filename = _report_export_service.export(
        db,
        log_id=log_id,
        keyword=keyword.strip() if keyword else None,
        status=status_value,
        level=level,
        tree_root=tree_root,
        current_user=current_user,
    )
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.delete(
    "/calc/logs",
    response_model=ApiResponse[DeletedCountVO],
)
def delete_all_calc_logs(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_CALC_DELETE)),
) -> ApiResponse[DeletedCountVO]:
    result = _service.delete_all_calc_logs(db)
    return ApiResponse.ok(data=result, message=f"已删除 {result.deleted_count} 条")


@router.delete(
    "/calc/logs/{log_id:int}",
    response_model=ApiResponse[None],
)
def delete_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_CALC_DELETE)),
) -> ApiResponse[None]:
    _service.delete_calc_log(db, log_id)
    return ApiResponse.deleted(message="计算日志已删除")


@router.get(
    "/calc/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_calc_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_CALC_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_ASSEMBLY_COST_CALC)
    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = AssemblyCostCalcResultVO.model_validate(result_raw) if result_raw else None
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
    dto: AssemblyCostCalcDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.ASSEMBLY_COST_CALC_RUN)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    accepted = _service.start_calc(db, dto, current_user=current_user)

    return ApiResponse.ok(
        data=accepted,
        message="已提交后台计算",
    )
