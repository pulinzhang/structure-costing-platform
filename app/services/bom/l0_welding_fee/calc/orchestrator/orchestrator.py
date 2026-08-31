"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

BOM 焊接费计算编排器（预备 → 引擎 → 收尾）

计算链：
  1. prepare_calc_run                   — 单价 / 成品拆解
  2. BatchCalculationEngine.run         — 逐 L0 计费
  3. persist_calc_result                — 格式化 VO 并落库
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.models.bom import BomL0WeldingFeeCalcLog
from app.schemas.dto.bom_l0_welding_fee_dto import BomL0WeldingFeeCalcDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.bom_l0_welding_fee_vo import (
    BomL0WeldingFeeCalcLogVO,
    BomL0WeldingFeeCalcReadyVO,
    BomL0WeldingFeeCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    TASK_TYPE_BOM_L0_WELDING_FEE_CALC,
    AsyncTaskService,
    WorkerTaskOutcome,
    calc_status_label,
    outcome_from_calc_status,
)
from app.services.bom.l0_welding_fee.calc.orchestrator.batch_engine import (
    BatchCalculationEngine,
)
from app.services.bom.l0_welding_fee.calc.orchestrator.deps import (
    L0WeldingFeeCalcDeps,
    build_l0_welding_fee_calc_deps,
)
from app.services.bom.l0_welding_fee.calc.orchestrator.persist import persist_calc_result
from app.services.bom.l0_welding_fee.calc.orchestrator.prep import prepare_calc_run
from app.services.bom.l0_welding_fee.calc.orchestrator.progress import (
    ProgressCallback,
    ProgressNotifier,
)
from app.services.bom.l0_welding_fee.calc.orchestrator.ready import collect_calc_ready

logger = logging.getLogger("service.bom.l0_welding_fee.calc")


class BomL0WeldingFeeCalcOrchestrator:
    """焊接费计算编排器。"""

    def __init__(self, deps: L0WeldingFeeCalcDeps | None = None) -> None:
        self._deps = deps or build_l0_welding_fee_calc_deps()
        self.calc_log_service = self._deps.calc_log_service

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomL0WeldingFeeCalcReadyVO:
        return collect_calc_ready(
            db,
            self._deps,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def begin_processing(
        self,
        db: Session,
        dto: BomL0WeldingFeeCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> BomL0WeldingFeeCalcLog:
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
    ) -> tuple[list[BomL0WeldingFeeCalcLogVO], int]:
        return self.calc_log_service.list_calc_logs(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            page=page,
            size=size,
        )

    def get_calc_log(self, db: Session, log_id: int) -> BomL0WeldingFeeCalcLogVO:
        return self.calc_log_service.get_calc_log(db, log_id)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        self.calc_log_service.delete_calc_log(db, log_id)

    def calculate(
        self,
        db: Session,
        dto: BomL0WeldingFeeCalcDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> BomL0WeldingFeeCalcResultVO:
        deps = self._deps
        progress = ProgressNotifier(progress_callback)

        ctx = prepare_calc_run(db, deps, dto, progress)
        batch = BatchCalculationEngine(deps).run(
            db,
            ctx=ctx,
            current_user=current_user,
            calc_batch_id=calc_batch_id,
            progress=progress,
        )
        result = persist_calc_result(
            db,
            deps,
            ctx=ctx,
            batch=batch,
            current_user=current_user,
            log_id=log_id,
            calc_batch_id=calc_batch_id,
            progress=progress,
        )
        logger.info(
            "焊接费计算完成: year=%s location=%s vehicle=%s version=%s "
            "created=%s updated=%s failed=%s skipped=%s missing_price=%s",
            ctx.year,
            ctx.location,
            ctx.vehicle_model,
            ctx.bom_version,
            result.created_count,
            result.updated_count,
            result.failed_count,
            result.skipped_approved_count,
            result.missing_price_count,
        )
        return result

    def start_calc(
        self,
        db: Session,
        dto: BomL0WeldingFeeCalcDTO,
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
        scoped = BomL0WeldingFeeCalcDTO(
            year=dto.year,
            location=dto.location.strip(),
            vehicle_model=dto.vehicle_model.strip(),
            bom_version=dto.bom_version.strip(),
        )
        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_BOM_L0_WELDING_FEE_CALC,
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
            label = calc_status_label(result.status)
            return outcome_from_calc_status(
                result.status,
                failed_message=(
                    f"计算失败：新增 {result.created_count}，更新 {result.updated_count}，"
                    f"失败 {result.failed_count}"
                ),
                completed_message=(
                    f"计算{label}：新增 {result.created_count}，"
                    f"更新 {result.updated_count}，失败 {result.failed_count}，"
                    f"缺单价 {result.missing_price_count}"
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
