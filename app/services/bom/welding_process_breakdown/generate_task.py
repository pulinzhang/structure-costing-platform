"""焊接工艺拆解：异步生成入队。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.exceptions.base import BusinessException
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownGenerateDTO,
)
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.bom_welding_process_breakdown_vo import (
    BomWeldingProcessBreakdownGenerateResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.async_task_service import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    TASK_TYPE_BOM_WELDING_PROCESS_BREAKDOWN_GENERATE,
    AsyncTaskService,
)
from app.services.async_task.worker_runner import WorkerTaskOutcome
from app.services.bom.welding_process_breakdown.generate_service import ProgressCallback
from app.services.masterdata.location.location_service import LocationService

if TYPE_CHECKING:
    from app.services.bom.welding_process_breakdown.service import (
        BomWeldingProcessBreakdownService,
    )


def start_generate(
    svc: BomWeldingProcessBreakdownService,
    db: Session,
    dto: BomWeldingProcessBreakdownGenerateDTO,
    current_user: UserVO,
) -> AsyncTaskAcceptedVO:
    location = LocationService().require_enabled(db, dto.location.strip())
    vehicle_model = dto.vehicle_model.strip()
    bom_version = dto.bom_version.strip()
    customer_name = (dto.customer_name or "").strip() or None
    lock_log = svc.begin_generate_processing(
        db,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        customer_name=customer_name,
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )
    log_id = lock_log.id
    calc_batch_id = lock_log.calc_batch_id
    started_at = lock_log.started_at
    scoped = BomWeldingProcessBreakdownGenerateDTO(
        location=location,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        customer_name=customer_name,
    )
    async_task_service = AsyncTaskService()
    task = async_task_service.create_task(
        task_type=TASK_TYPE_BOM_WELDING_PROCESS_BREAKDOWN_GENERATE,
        message="已提交拆解队列",
        operator_id=current_user.id,
        operator_name=display_name(current_user),
    )

    def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
        try:
            result = svc.generate_from_bom(
                worker_db,
                scoped,
                current_user,
                progress_callback=on_progress,
                log_id=log_id,
                calc_batch_id=calc_batch_id,
                started_at=started_at,
            )
        except BusinessException as exc:
            fail_message = exc.message
            return WorkerTaskOutcome(
                status=STATUS_FAILED,
                progress=100,
                message=fail_message,
                result=BomWeldingProcessBreakdownGenerateResultVO(
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                    status="failed",
                    message=fail_message,
                    calc_batch_id=calc_batch_id,
                    log_id=log_id,
                    detail_text=fail_message,
                ).model_dump(),
            )
        return WorkerTaskOutcome(
            status=STATUS_COMPLETED,
            message=result.message,
            result=result.model_dump(),
        )

    def on_crash(worker_db: Session, error: BaseException) -> None:
        svc.mark_generate_log_failed(
            worker_db,
            log_id=log_id,
            message=str(error),
            detail_text=f"拆解异常: {error}",
        )

    async_task_service.submit_session_worker(
        task.task_id,
        start_message="后台开始拆解...",
        work=work,
        on_crash=on_crash,
        crash_message=lambda error: f"拆解异常: {error}",
    )
    return AsyncTaskAcceptedVO(task_id=task.task_id)
