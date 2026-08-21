"""
冲压零件价格计算 API
异步计算触发 + 计算就绪检查 + 计算日志/任务进度
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.common.permissions.codes import Perm
from app.database import DatabaseConfig, get_db
from app.deps.permissions import require_any_perm, require_perm
from app.exceptions.base import BusinessException
from app.schemas.common.page_result import PageResult
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.stamping_part_cost_vo import (
    StampingPartCostCalcLogVO,
    StampingPartCostCalcReadyVO,
    StampingPartCostCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    TASK_TYPE_STAMPING_PART_COST_CALC,
    AsyncTaskService,
)
from app.services.costing.stamping_part_cost.stamping_part_cost_service import (
    DUPLICATE_SCOPE_CALC_MESSAGE,
    DuplicateScopeCalcError,
    StampingPartCostService,
)
from app.utils.response import ApiResponse


router = APIRouter(
    prefix="/api/costing/stamping-part-cost",
    tags=["冲压零件价格计算"],
)

_service = StampingPartCostService()
_async_task_service = AsyncTaskService()


def _process_calc_in_background(
    task_id: str,
    log_id: int,
    calc_batch_id: str,
    year: int,
    month: int,
    location: str,
    stamping_supplier: str,
    vehicle_model: str | None,
    version: str | None,
    current_user: UserVO,
) -> None:
    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()

    def on_progress(progress: int, msg: str) -> None:
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_RUNNING,
            progress=progress,
            message=msg,
        )

    try:
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_RUNNING,
            progress=1,
            message="后台开始计算...",
        )
        dto = StampingPartCostCalcDTO(
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )
        result = _service.calculate(
            db,
            dto,
            current_user=current_user,
            progress_callback=on_progress,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
        )
        if result.status == "failed":
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_FAILED,
                progress=100,
                message=(
                    f"计算失败：成功 {result.success_count}，失败 {result.failed_count}"
                ),
                result=result.model_dump(),
            )
        else:
            label = {"success": "成功", "partial": "部分成功"}.get(
                result.status, result.status
            )
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_COMPLETED,
                progress=100,
                message=(
                    f"计算{label}：成功 {result.success_count}，"
                    f"失败 {result.failed_count}"
                ),
                result=result.model_dump(),
            )
    except Exception as error:
        try:
            db.rollback()
        except Exception:
            pass
        try:
            _service.mark_log_failed(
                db,
                log_id=log_id,
                detail_text=f"计算失败: {error}",
            )
        except Exception:
            pass
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_FAILED,
            progress=0,
            message=str(error),
        )
    finally:
        db.close()


@router.get(
    "/filters/years",
    response_model=ApiResponse[List[int]],
)
def list_years(
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(
        require_any_perm(
            Perm.STAMPING_PART_COST_VIEW,
            Perm.STAMPING_PART_COST_CALC_VIEW,
        )
    ),
) -> ApiResponse[List[int]]:
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
    stamping_supplier: str | None = Query(None),
    vehicle_model: str | None = Query(None),
    version: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_CALC_VIEW)),
) -> ApiResponse[StampingPartCostCalcReadyVO]:
    data = _service.get_calc_ready(
        db,
        year=year,
        month=month,
        location=location or None,
        stamping_supplier=stamping_supplier or None,
        vehicle_model=vehicle_model or None,
        version=version or None,
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
    if not record:
        raise HTTPException(status_code=404, detail="计算日志不存在")
    return ApiResponse.ok(data=record)


@router.delete(
    "/calc/logs/{log_id}",
    response_model=ApiResponse[None],
)
def delete_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_CALC_DELETE)),
) -> ApiResponse[None]:
    try:
        deleted = _service.delete_calc_log(db, log_id)
    except BusinessException as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="计算日志不存在")
    return ApiResponse.deleted(message="计算日志已删除")


@router.get(
    "/calc/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_calc_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_CALC_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    task = _async_task_service.get_task_snapshot(task_id)
    if task is None or task.get("task_type") != TASK_TYPE_STAMPING_PART_COST_CALC:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = (
        StampingPartCostCalcResultVO.model_validate(result_raw)
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
    dto: StampingPartCostCalcDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STAMPING_PART_COST_CALC_RUN)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    try:
        lock_log = _service.begin_processing(
            db,
            dto,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
    except DuplicateScopeCalcError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error) or DUPLICATE_SCOPE_CALC_MESSAGE,
        ) from error
    except BusinessException as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    task = _async_task_service.create_task(
        task_type=TASK_TYPE_STAMPING_PART_COST_CALC,
        message="已提交计算队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )
    AsyncTaskService.submit(
        _process_calc_in_background,
        task.task_id,
        lock_log.id,
        lock_log.calc_batch_id,
        dto.year,
        dto.month,
        dto.location,
        dto.stamping_supplier,
        dto.vehicle_model,
        dto.version,
        current_user,
    )
    return ApiResponse.ok(
        data=AsyncTaskAcceptedVO(task_id=task.task_id),
        message="已提交后台计算",
    )
