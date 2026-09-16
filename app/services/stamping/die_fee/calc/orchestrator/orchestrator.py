"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

冲压年度模具费计算编排器（预备 → 引擎 → 收尾）

计算链：
  1. prepare_calc_run                   — 布点 / 单价 / 已审冲突
  2. BatchCalculationEngine.run         — 共模扫描与身份落库载荷
  3. persist_calc_result                — 清旧结果并落库
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.exceptions.base import BusinessException
from app.schemas.common import DeletedCountVO
from app.schemas.dto.stamping_die_fee_dto import StampingDieFeeCalcDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.stamping_die_fee_vo import (
    StampingDieFeeCalcLogVO,
    StampingDieFeeCalcReadyVO,
    StampingDieFeeCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    TASK_TYPE_STAMPING_DIE_FEE_CALC,
    AsyncTaskService,
    WorkerTaskOutcome,
    calc_status_label,
    outcome_from_calc_status,
)
from app.services.async_task.worker_runner import ProgressCallback
from app.services.masterdata.vehicle_model import VehicleModelService
from app.services.stamping.die_fee.calc.constants import APPROVED_SCOPE_MESSAGE
from app.services.stamping.die_fee.calc.orchestrator.batch_engine import (
    BatchCalculationEngine,
)
from app.services.stamping.die_fee.calc.orchestrator.deps import (
    DieFeeCalcDeps,
    build_die_fee_calc_deps,
)
from app.services.stamping.die_fee.calc.orchestrator.identity import strip_optional
from app.services.stamping.die_fee.calc.orchestrator.persist import persist_calc_result
from app.services.stamping.die_fee.calc.orchestrator.prep import (
    count_approved,
    prepare_calc_run,
)
from app.services.stamping.die_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.stamping.die_fee.calc.orchestrator.ready import collect_calc_ready


class StampingDieFeeCalcOrchestrator:
    """冲压年度模具费计算编排器。"""

    def __init__(self, deps: DieFeeCalcDeps | None = None) -> None:
        self._deps = deps or build_die_fee_calc_deps()
        self.calc_log_service = self._deps.calc_log_service

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> StampingDieFeeCalcReadyVO:
        return collect_calc_ready(
            db,
            self._deps,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
        )

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        stamping_supplier: str | None = None,
        version: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[StampingDieFeeCalcLogVO], int]:
        return self.calc_log_service.list_calc_logs(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            stamping_supplier=strip_optional(stamping_supplier),
            version=strip_optional(version),
            page=page,
            size=size,
        )

    def get_calc_log(self, db: Session, log_id: int) -> StampingDieFeeCalcLogVO:
        return self.calc_log_service.get_calc_log(db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        self.calc_log_service.delete_calc_log(db, log_id)

    def delete_all_calc_logs(self, db: Session) -> DeletedCountVO:
        return self.calc_log_service.delete_all_logs(db)

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        detail_text: str,
    ) -> None:
        self.calc_log_service.mark_log_failed(db, log_id=log_id, detail_text=detail_text)

    def calculate(
        self,
        db: Session,
        dto: StampingDieFeeCalcDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> StampingDieFeeCalcResultVO:
        progress = ProgressNotifier(progress_callback)
        ctx = prepare_calc_run(db, self._deps, dto, progress)
        batch = BatchCalculationEngine(self._deps.part_calculator).run(
            ctx=ctx,
            dto=dto,
            current_user=current_user,
            progress=progress,
        )
        return persist_calc_result(
            db,
            self._deps,
            dto=dto,
            ctx=ctx,
            batch=batch,
            current_user=current_user,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
            progress=progress,
        )

    def start_calc(
        self,
        db: Session,
        dto: StampingDieFeeCalcDTO,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        canonical, vehicle_model = VehicleModelService().require_overlaps_year(
            db, dto.location, dto.vehicle_model, dto.year
        )
        dto = dto.model_copy(update={"location": canonical, "vehicle_model": vehicle_model})
        if count_approved(db, self._deps, dto):
            raise BusinessException(APPROVED_SCOPE_MESSAGE, code=409)

        lock_log = self.calc_log_service.begin_processing(
            db,
            dto,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
        log_id = lock_log.id
        calc_batch_id = lock_log.calc_batch_id
        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_STAMPING_DIE_FEE_CALC,
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
                    f"计算失败：入库 {result.success_count}，跳过 {result.skipped_no_die_count}"
                ),
                completed_message=(
                    f"计算{label}：入库 {result.success_count}，"
                    f"跳过 {result.skipped_no_die_count}"
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
