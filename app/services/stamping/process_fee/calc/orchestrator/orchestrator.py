"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

冲压加工费计算编排器（预备 → 引擎 → 收尾）

计算链：
  1. prepare_calc_run                   — 冲次单价 / 零件
  2. BatchCalculationEngine.run         — 逐件计费
  3. persist_calc_result                — 格式化 VO 并落库
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.models.stamping import StampingProcessFeeCalcLog
from app.schemas.dto.stamping_process_fee_dto import StampingProcessFeeCalcDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.stamping_process_fee_vo import (
    StampingProcessFeeCalcLogVO,
    StampingProcessFeeCalcReadyVO,
    StampingProcessFeeCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    TASK_TYPE_STAMPING_PROCESS_FEE_CALC,
    AsyncTaskService,
    WorkerTaskOutcome,
    calc_status_label,
    outcome_from_calc_status,
)
from app.services.stamping.process_fee.calc.models import ProgressCallback
from app.services.stamping.process_fee.calc.orchestrator.batch_engine import (
    BatchCalculationEngine,
)
from app.services.stamping.process_fee.calc.orchestrator.deps import (
    ProcessFeeCalcDeps,
    build_process_fee_calc_deps,
)
from app.services.stamping.process_fee.calc.orchestrator.persist import persist_calc_result
from app.services.stamping.process_fee.calc.orchestrator.prep import prepare_calc_run
from app.services.stamping.process_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.stamping.process_fee.calc.orchestrator.ready import collect_calc_ready

logger = logging.getLogger("service.stamping.process_fee.calc")


class StampingProcessFeeCalcOrchestrator:
    """冲压加工费计算编排器。"""

    def __init__(self, deps: ProcessFeeCalcDeps | None = None) -> None:
        self._deps = deps or build_process_fee_calc_deps()
        self.calc_log_service = self._deps.calc_log_service

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> StampingProcessFeeCalcReadyVO:
        return collect_calc_ready(
            db,
            self._deps,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )

    def begin_processing(
        self,
        db: Session,
        dto: StampingProcessFeeCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> StampingProcessFeeCalcLog:
        return self.calc_log_service.begin_processing(
            db,
            dto,
            operator_id=operator_id,
            operator_name=operator_name,
        )

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        detail_text: str,
    ) -> None:
        self.calc_log_service.mark_log_failed(db, log_id=log_id, detail_text=detail_text)

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[StampingProcessFeeCalcLogVO], int]:
        return self.calc_log_service.list_calc_logs(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            page=page,
            size=size,
        )

    def get_calc_log(self, db: Session, log_id: int) -> StampingProcessFeeCalcLogVO:
        return self.calc_log_service.get_calc_log(db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        self.calc_log_service.delete_calc_log(db, log_id)

    def calculate(
        self,
        db: Session,
        dto: StampingProcessFeeCalcDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> StampingProcessFeeCalcResultVO:
        deps = self._deps
        progress = ProgressNotifier(progress_callback)

        ctx = prepare_calc_run(db, deps, dto, progress)
        batch = BatchCalculationEngine(deps).run(
            db,
            ctx=ctx,
            dto=dto,
            current_user=current_user,
            progress=progress,
        )
        result = persist_calc_result(
            db,
            deps,
            dto=dto,
            ctx=ctx,
            batch=batch,
            current_user=current_user,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
            progress=progress,
        )

        logger.info(
            "冲压加工费计算完成: year=%s location=%s supplier=%s "
            "success=%s failed=%s zero_fee=%s skipped_approved=%s",
            dto.year,
            ctx.location,
            ctx.supplier,
            result.success_count,
            result.failed_count,
            result.zero_fee_count,
            result.skipped_approved_count,
        )
        return result

    def start_calc(
        self,
        db: Session,
        dto: StampingProcessFeeCalcDTO,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        lock_log = self.begin_processing(
            db,
            dto,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
        log_id = lock_log.id
        calc_batch_id = lock_log.calc_batch_id
        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_STAMPING_PROCESS_FEE_CALC,
            message="已提交计算队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            result = self.calculate(
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
                failed_message=(
                    f"计算失败：成功 {result.success_count}，失败 {result.failed_count}"
                ),
                completed_message=(
                    f"计算{label}：成功 {result.success_count}，"
                    f"失败 {result.failed_count}，零价 {result.zero_fee_count}"
                ),
                result=result.model_dump(),
            )

        def on_crash(worker_db: Session, error: BaseException) -> None:
            self.mark_log_failed(
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
