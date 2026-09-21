"""冲压零件核价：计算入队与计算日志。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.models.costing import StampingPartCostCalcLog
from app.schemas.common.deleted_count import DeletedCountVO
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.stamping_part_cost_vo import (
    StampingPartCostCalcLogVO,
    StampingPartCostCalcReadyVO,
    StampingPartCostCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.service import (
    TASK_TYPE_STAMPING_PART_COST_CALC,
    AsyncTaskService,
)
from app.services.async_task.worker_runner import (
    WorkerTaskOutcome,
    calc_status_label,
    outcome_from_calc_status,
)
from app.services.costing.stamping_part_cost.calc.models import ProgressCallback
from app.services.masterdata.vehicle_model.service import VehicleModelService

if TYPE_CHECKING:
    from app.services.costing.stamping_part_cost.service import (
        StampingPartCostService,
    )


def get_calc_ready(
    svc: StampingPartCostService,
    db: Session,
    *,
    year: int,
    month: int | None = None,
    location: str | None = None,
    vehicle_model: str | None = None,
) -> StampingPartCostCalcReadyVO:
    return svc.orchestrator.get_calc_ready(
        db,
        year=year,
        month=month,
        location=location,
        vehicle_model=vehicle_model,
    )


def begin_processing(
    svc: StampingPartCostService,
    db: Session,
    dto: StampingPartCostCalcDTO,
    *,
    operator_id: int | None,
    operator_name: str | None,
) -> StampingPartCostCalcLog:
    return svc.orchestrator.begin_processing(
        db,
        dto,
        operator_id=operator_id,
        operator_name=operator_name,
    )


def mark_log_failed(
    svc: StampingPartCostService,
    db: Session,
    *,
    log_id: int,
    detail_text: str,
) -> None:
    svc.orchestrator.mark_log_failed(db, log_id=log_id, detail_text=detail_text)


def calculate(
    svc: StampingPartCostService,
    db: Session,
    dto: StampingPartCostCalcDTO,
    current_user: UserVO,
    *,
    progress_callback: ProgressCallback | None = None,
    log_id: int | None = None,
    calc_batch_id: str | None = None,
) -> StampingPartCostCalcResultVO:
    return svc.orchestrator.calculate(
        db,
        dto,
        current_user,
        progress_callback=progress_callback,
        log_id=log_id,
        calc_batch_id=calc_batch_id,
    )


def start_calc(
    svc: StampingPartCostService,
    db: Session,
    dto: StampingPartCostCalcDTO,
    current_user: UserVO,
) -> AsyncTaskAcceptedVO:
    canonical, vehicle_model = VehicleModelService().require_introducible(
        db, dto.location, dto.vehicle_model, dto.year, dto.month
    )
    dto = dto.model_copy(update={"location": canonical, "vehicle_model": vehicle_model})
    lock_log = begin_processing(
        svc,
        db,
        dto,
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )
    log_id = lock_log.id
    calc_batch_id = lock_log.calc_batch_id
    async_task_service = AsyncTaskService()
    task = async_task_service.create_task(
        task_type=TASK_TYPE_STAMPING_PART_COST_CALC,
        message="已提交计算队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )

    def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
        result = calculate(
            svc,
            worker_db,
            dto,
            current_user=current_user,
            progress_callback=on_progress,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
        )
        label = calc_status_label(result.status)
        return outcome_from_calc_status(
            result.status,
            failed_message=(f"计算失败：成功 {result.success_count}，失败 {result.failed_count}"),
            completed_message=(
                f"计算{label}：成功 {result.success_count}，" f"失败 {result.failed_count}"
            ),
            result=result.model_dump(),
        )

    def on_crash(worker_db: Session, error: BaseException) -> None:
        mark_log_failed(
            svc,
            worker_db,
            log_id=log_id,
            detail_text=f"计算失败: {error}",
        )

    async_task_service.submit_session_worker(
        task.task_id,
        start_message="后台开始计算...",
        work=work,
        on_crash=on_crash,
    )
    return AsyncTaskAcceptedVO(task_id=task.task_id)


def list_calc_logs(
    svc: StampingPartCostService,
    db: Session,
    *,
    year: int | None = None,
    month: int | None = None,
    location: str | None = None,
    stamping_supplier: str | None = None,
    page: int = 1,
    size: int = 20,
) -> tuple[list[StampingPartCostCalcLogVO], int]:
    return svc.orchestrator.calc_log_service.list_calc_logs(
        db,
        year=year,
        month=month,
        location=location,
        stamping_supplier=stamping_supplier,
        page=page,
        size=size,
    )


def get_calc_log(
    svc: StampingPartCostService, db: Session, log_id: int
) -> StampingPartCostCalcLogVO:
    return svc.orchestrator.calc_log_service.get_calc_log(db, log_id)


def delete_calc_log(svc: StampingPartCostService, db: Session, log_id: int) -> None:
    svc.orchestrator.calc_log_service.delete_calc_log(db, log_id)


def delete_all_calc_logs(svc: StampingPartCostService, db: Session) -> DeletedCountVO:
    return svc.orchestrator.calc_log_service.delete_all_logs(db)
