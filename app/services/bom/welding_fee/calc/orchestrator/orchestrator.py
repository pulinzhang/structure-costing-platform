"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

BOM 焊接费计算编排器（预备 → 引擎 → 收尾）

计算链：
  1. prepare_calc_run                   — 单价 / 成品拆解
  2. BatchCalculationEngine.run         — 逐 L0 计费
  3. persist_calc_result                — 格式化 VO 并落库
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.models.bom import BomWeldingFeeCalcLog
from app.schemas.common import DeletedCountVO
from app.schemas.dto.bom_welding_fee_dto import BomWeldingFeeCalcDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.bom_welding_fee_vo import (
    BomWeldingFeeCalcLogVO,
    BomWeldingFeeCalcReadyVO,
    BomWeldingFeeCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    TASK_TYPE_BOM_WELDING_FEE_CALC,
    AsyncTaskService,
    WorkerTaskOutcome,
    outcome_from_calc_status,
)
from app.services.bom.welding_fee.calc.orchestrator.batch_engine import (
    BatchCalculationEngine,
)
from app.services.bom.welding_fee.calc.orchestrator.deps import (
    WeldingFeeCalcDeps,
    build_welding_fee_calc_deps,
)
from app.services.bom.welding_fee.calc.orchestrator.persist import persist_calc_result
from app.services.bom.welding_fee.calc.orchestrator.prep import prepare_calc_run
from app.services.bom.welding_fee.calc.orchestrator.progress import (
    ProgressCallback,
    ProgressNotifier,
)
from app.services.bom.welding_fee.calc.orchestrator.ready import collect_calc_ready
from app.services.bom.welding_fee.calc.staff_report import calc_finish_toast
from app.services.masterdata.vehicle_model import VehicleModelService


class BomWeldingFeeCalcOrchestrator:
    """焊接费计算编排器。"""

    def __init__(self, deps: WeldingFeeCalcDeps | None = None) -> None:
        self._deps = deps or build_welding_fee_calc_deps()
        self.calc_log_service = self._deps.calc_log_service

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
    ) -> BomWeldingFeeCalcReadyVO:
        return collect_calc_ready(
            db,
            self._deps,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
        )

    def begin_processing(
        self,
        db: Session,
        dto: BomWeldingFeeCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> BomWeldingFeeCalcLog:
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
        self.calc_log_service.mark_failed(db, log_id=log_id, detail_text=detail_text)

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[BomWeldingFeeCalcLogVO], int]:
        return self.calc_log_service.list_calc_logs(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            page=page,
            size=size,
        )

    def get_calc_log(self, db: Session, log_id: int) -> BomWeldingFeeCalcLogVO:
        return self.calc_log_service.get_calc_log(db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        self.calc_log_service.delete_calc_log(db, log_id)

    def delete_all_calc_logs(self, db: Session) -> DeletedCountVO:
        return self.calc_log_service.delete_all_logs(db)

    def calculate(
        self,
        db: Session,
        dto: BomWeldingFeeCalcDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> BomWeldingFeeCalcResultVO:
        progress = ProgressNotifier(progress_callback)
        ctx = prepare_calc_run(db, self._deps, dto, progress)
        batch = BatchCalculationEngine(self._deps).run(
            db,
            ctx=ctx,
            current_user=current_user,
            calc_batch_id=calc_batch_id,
            progress=progress,
        )
        return persist_calc_result(
            db,
            self._deps,
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
        dto: BomWeldingFeeCalcDTO,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        canonical, vehicle_model = VehicleModelService().require_overlaps_year(
            db, dto.location, dto.vehicle_model, dto.year
        )
        scoped = BomWeldingFeeCalcDTO(
            year=dto.year,
            location=canonical,
            vehicle_model=vehicle_model,
            levels=dto.levels,
        )
        lock_log = self.begin_processing(
            db,
            scoped,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
        log_id = lock_log.id
        calc_batch_id = lock_log.calc_batch_id
        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_BOM_WELDING_FEE_CALC,
            message="已提交计算队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            result = self.calculate(
                worker_db,
                scoped,
                current_user,
                progress_callback=on_progress,
                log_id=log_id,
                calc_batch_id=calc_batch_id,
            )
            finish_msg = calc_finish_toast(
                biz_status=result.status,
                created_count=result.created_count,
                updated_count=result.updated_count,
                failed_count=result.failed_count,
                missing_price_count=result.missing_price_count,
            )
            return outcome_from_calc_status(
                result.status,
                failed_message=finish_msg,
                completed_message=finish_msg,
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
