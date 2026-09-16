"""
冲压零件价格计算 API
异步计算触发 + 计算就绪检查 + 计算日志/任务进度
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_any_perm, require_perm
from app.schemas.common import DeletedCountVO, PageResult
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.stamping_part_cost_vo import (
    StampingPartCostCalcLogVO,
    StampingPartCostCalcReadyVO,
    StampingPartCostCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_PENDING,
    TASK_TYPE_STAMPING_PART_COST_CALC,
    AsyncTaskService,
)
from app.services.costing.stamping_part_cost.stamping_part_cost_service import (
    StampingPartCostService,
)
from app.utils.response import ApiResponse

router = APIRouter(
    prefix="/api/costing/stamping-part-cost",
    tags=["冲压零件价格计算"],
)

_service = StampingPartCostService()
_async_task_service = AsyncTaskService()


@router.get(
    "/filters/years",
    response_model=ApiResponse[list[int]],
)
def list_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STAMPING_PART_COST_VIEW,
            Perm.STAMPING_PART_COST_CALC_VIEW,
        )
    ),
) -> ApiResponse[list[int]]:
    years = _service.list_years(db)
    return ApiResponse.ok(data=years)


@router.get(
    "/calc/ready",
    response_model=ApiResponse[StampingPartCostCalcReadyVO],
)
def get_calc_ready(
    year: int = Query(..., ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    location: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_CALC_VIEW)),
) -> ApiResponse[StampingPartCostCalcReadyVO]:
    data = _service.get_calc_ready(
        db,
        year=year,
        month=month,
        location=location or None,
        vehicle_model=vehicle_model or None,
    )
    return ApiResponse.ok(data=data)


@router.get(
    "/calc/logs",
    response_model=ApiResponse[PageResult[StampingPartCostCalcLogVO]],
)
def list_calc_logs(
    year: int | None = Query(None),
    month: int | None = Query(None),
    location: str | None = Query(None),
    stamping_supplier: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_CALC_VIEW)),
) -> ApiResponse[PageResult[StampingPartCostCalcLogVO]]:
    rows, total = _service.list_calc_logs(
        db,
        year=year,
        month=month,
        location=location,
        stamping_supplier=stamping_supplier,
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
    response_model=ApiResponse[StampingPartCostCalcLogVO],
)
def get_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_CALC_VIEW)),
) -> ApiResponse[StampingPartCostCalcLogVO]:
    record = _service.get_calc_log(db, log_id)
    return ApiResponse.ok(data=record)


@router.delete(
    "/calc/logs",
    response_model=ApiResponse[DeletedCountVO],
)
def delete_all_calc_logs(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_CALC_DELETE)),
) -> ApiResponse[DeletedCountVO]:
    result = _service.delete_all_calc_logs(db)
    return ApiResponse.ok(data=result, message=f"已删除 {result.deleted_count} 条")


@router.delete(
    "/calc/logs/{log_id}",
    response_model=ApiResponse[None],
)
def delete_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_CALC_DELETE)),
) -> ApiResponse[None]:
    _service.delete_calc_log(db, log_id)
    return ApiResponse.deleted(message="计算日志已删除")


@router.get(
    "/calc/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_calc_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_CALC_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    task = _async_task_service.require_snapshot(task_id, TASK_TYPE_STAMPING_PART_COST_CALC)
    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = StampingPartCostCalcResultVO.model_validate(result_raw) if result_raw else None
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
    dto: StampingPartCostCalcDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_CALC_RUN)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    accepted = _service.start_calc(db, dto, current_user=current_user)

    return ApiResponse.ok(
        data=accepted,
        message="已提交后台计算",
    )
