"""
钢材价格计算 API
触发编排（异步任务）+ 计算历史（含 detail_text 全过程）
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.common.permissions.codes import Perm
from app.database import DatabaseConfig, get_db
from app.common.audit import display_name
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.steel_price_dto import SteelPriceCalcDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO, AsyncTaskProgressVO
from app.schemas.vo.steel_price_vo import SteelPriceCalcLogVO, SteelPriceCalcResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (

    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    TASK_TYPE_STEEL_PRICE_CALC,
    AsyncTaskService,
)
from app.services.costing.steel_price.calc import (
    SteelPriceCalcOrchestrator,
    SteelPriceCalcRequest,
)
from app.services.costing.steel_price.calc.status import (
    DUPLICATE_PERIOD_CALC_MESSAGE,
    DuplicatePeriodCalcError,
)
from app.utils.logging_config import get_logger
from app.utils.response import ApiResponse


logger = get_logger("router.steel_price.calc")

router = APIRouter(prefix="/api/costing/steel-price", tags=["钢材价格计算"])

_calc_orchestrator = SteelPriceCalcOrchestrator()
_async_task_service = AsyncTaskService()


def _to_result_vo(result: Any) -> SteelPriceCalcResultVO:
    return SteelPriceCalcResultVO(
        calc_batch_id=result.calc_batch_id,
        log_id=result.log_id,
        status=result.status,
        year=result.year,
        month=result.month,
        location=result.location,
        stamping_supplier=result.stamping_supplier,
        vehicle_model=result.vehicle_model,
        material_count=result.material_count,
        enriched_count=result.enriched_count,
        no_base_count=result.no_base_count,
        created_count=result.created_count,
        updated_count=result.updated_count,
        skipped_approved_count=result.skipped_approved_count,
        failed_count=result.failed_count,
        detail_text=result.detail_text,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )


def _process_steel_price_calc_in_background(
    task_id: str,
    log_id: int,
    calc_batch_id: str,
    year: int,
    month: int,
    location: str,
    stamping_supplier: str | None,
    vehicle_model: str | None,
    started_at_iso: str | None,
    current_user: UserVO,
) -> None:
    """后台线程执行钢价计算；独立 Session，不复用请求 db。"""
    from datetime import datetime

    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()

    def on_progress(progress: int, msg: str) -> None:
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_RUNNING,
            progress=progress,
            message=msg,
        )

    started_at = None
    if started_at_iso:
        try:
            started_at = datetime.fromisoformat(started_at_iso)
        except ValueError:
            started_at = None

    try:
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_RUNNING,
            progress=1,
            message="后台开始计算...",
        )
        result = _calc_orchestrator.calculate(
            db,
            SteelPriceCalcRequest(
                year=year,
                month=month,
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
            ),
            progress_callback=on_progress,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
            started_at=started_at,
            current_user=current_user,
        )
        result_vo = _to_result_vo(result)
        if result.status == "failed":
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_FAILED,
                progress=100,
                message=(
                    f"计算失败：新增 {result.created_count}，"
                    f"更新 {result.updated_count}，失败 {result.failed_count}"
                ),
                result=result_vo.model_dump(),
            )
        else:
            status_label = {
                "success": "成功",
                "partial": "部分成功",
            }.get(result.status, result.status)
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_COMPLETED,
                progress=100,
                message=(
                    f"计算{status_label}：新增 {result.created_count}，"
                    f"更新 {result.updated_count}，失败 {result.failed_count}"
                ),
                result=result_vo.model_dump(),
            )
    except Exception as error:
        logger.exception("钢价计算异常: task_id=%s log_id=%s", task_id, log_id)
        try:
            db.rollback()
        except Exception:
            pass
        try:
            _calc_orchestrator.mark_log_failed(
                db,
                log_id=log_id,
                message=str(error),
                detail_text=f"计算异常: {error}",
            )
        except Exception:
            logger.exception("释放计算锁失败: log_id=%s", log_id)
        _async_task_service.update_task_standalone(
            task_id,
            status=STATUS_FAILED,
            progress=0,
            message=f"计算异常: {error}",
        )
    finally:
        db.close()


@router.get(
    "/calc/logs",
    response_model=ApiResponse[PageResult[SteelPriceCalcLogVO]],
)
def list_calc_logs(
    year: int | None = Query(None, ge=2000, le=2100, description="核价年度"),
    month: int | None = Query(None, ge=1, le=12, description="核价月份"),
    location: str | None = Query(None, description="生产基地"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_VIEW)),
) -> ApiResponse[PageResult[SteelPriceCalcLogVO]]:
    """分页查询钢价计算历史（含 detail_text）。"""
    records, total = _calc_orchestrator.list_logs(
        db,
        year=year,
        month=month,
        location=location,
        page=page,
        size=size,
    )
    return ApiResponse.list_(
        items=records,
        total=total,
        page=page,
        page_size=size,
    )


@router.get(
    "/calc/logs/{log_id}",
    response_model=ApiResponse[SteelPriceCalcLogVO],
)
def get_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_VIEW)),
) -> ApiResponse[SteelPriceCalcLogVO]:
    """查看单次计算全过程（detail_text）。"""
    record = _calc_orchestrator.get_log(db, log_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="计算记录不存在")
    return ApiResponse.ok(data=record)


@router.delete(
    "/calc/logs/{log_id}",
    response_model=ApiResponse[None],
)
def delete_calc_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_DELETE)),
) -> ApiResponse[None]:
    """删除一条计算历史日志（不影响已落库的钢材价格结果）。"""
    try:
        deleted = _calc_orchestrator.delete_log(db, log_id)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="计算记录不存在")
    return ApiResponse.deleted(message="删除成功")


@router.get(
    "/calc/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_steel_price_calc_task_progress(
    task_id: str,
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    """查询钢价计算任务进度。"""
    task = _async_task_service.get_task_snapshot(task_id)
    if task is None or task.get("task_type") != TASK_TYPE_STEEL_PRICE_CALC:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    result_raw = AsyncTaskService.parse_result_json(task.get("result_json"))
    result = (
        SteelPriceCalcResultVO.model_validate(result_raw) if result_raw else None
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
def calculate_steel_prices(
    body: SteelPriceCalcDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.STEEL_PRICE_CALC_RUN)),
) -> ApiResponse[AsyncTaskAcceptedVO]:
    """
    按筛选条件提交钢价联动计算（异步）。

    同一年度+月份+基地若已有 processing，直接拒绝重复提交。
    立即返回 task_id，前端轮询 /calc/tasks/{task_id} 获取进度。
    """
    location = (body.location or "").strip()
    if not location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="计算钢价必须指定生产基地",
        )

    request = SteelPriceCalcRequest(
        year=body.year,
        month=body.month,
        location=location,
        stamping_supplier=body.stamping_supplier,
        vehicle_model=body.vehicle_model,
    )

    try:
        lock_log = _calc_orchestrator.begin_processing(
            db,
            request,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
    except DuplicatePeriodCalcError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error) or DUPLICATE_PERIOD_CALC_MESSAGE,
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    task = _async_task_service.create_task(
        task_type=TASK_TYPE_STEEL_PRICE_CALC,
        message="已提交计算队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )
    started_at_iso = (
        lock_log.started_at.isoformat(timespec="seconds") if lock_log.started_at else None
    )
    AsyncTaskService.submit(
        _process_steel_price_calc_in_background,
        task.task_id,
        lock_log.id,
        lock_log.calc_batch_id,
        body.year,
        body.month,
        location,
        body.stamping_supplier,
        body.vehicle_model,
        started_at_iso,
        current_user,
    )

    return ApiResponse.ok(
        data=AsyncTaskAcceptedVO(task_id=task.task_id),
        message="已提交后台计算",
    )
