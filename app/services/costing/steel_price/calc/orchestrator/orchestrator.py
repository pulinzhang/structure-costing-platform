"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

钢价计算编排器（预备 → 管道 → 收尾）

计算链：
  1. prepare_calc_run                   — 批次与过程日志头
  2. SteelPricePipeline.run             — 材料 / 基价 / 加减价 / 落库
  3. persist_calc_result                — 写过程日志
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.exceptions.base import BusinessException
from app.models.costing import SteelPriceCalcLog
from app.schemas.common.deleted_count import DeletedCountVO
from app.schemas.dto.steel_price_dto import SteelPriceCalcDTO
from app.schemas.vo.async_task_vo import AsyncTaskAcceptedVO
from app.schemas.vo.steel_price_vo import SteelPriceCalcLogVO, SteelPriceCalcResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.async_task.service import (
    TASK_TYPE_STEEL_PRICE_CALC,
    AsyncTaskService,
)
from app.services.async_task.worker_runner import (
    WorkerTaskOutcome,
    calc_status_label,
    outcome_from_calc_status,
)
from app.services.costing.steel_price.calc.coverage import assert_steel_calc_thickness
from app.services.costing.steel_price.calc.models import (
    SteelPriceCalcRequest,
    SteelPriceCalcResult,
)
from app.services.costing.steel_price.calc.orchestrator.deps import (
    SteelPriceCalcDeps,
    build_steel_price_calc_deps,
)
from app.services.costing.steel_price.calc.orchestrator.persist import persist_calc_result
from app.services.costing.steel_price.calc.orchestrator.pipeline import SteelPricePipeline
from app.services.costing.steel_price.calc.orchestrator.prep import prepare_calc_run
from app.services.costing.steel_price.calc.orchestrator.progress import (
    ProgressCallback,
    ProgressNotifier,
)
from app.services.masterdata.location.service import LocationService


class SteelPriceCalcOrchestrator:
    """钢材价格计算编排器。"""

    def __init__(self, deps: SteelPriceCalcDeps | None = None) -> None:
        self._deps = deps or build_steel_price_calc_deps()
        self.calc_log_service = self._deps.calc_log_service

    def begin_processing(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
        *,
        operator_id: int | None = None,
        operator_name: str | None = None,
    ) -> SteelPriceCalcLog:
        """提交前写入 processing 期别锁。"""
        location = request.location.strip()
        if not location:
            raise BusinessException("计算钢价必须指定生产基地 location")
        return self.calc_log_service.begin_processing(
            db,
            year=request.year,
            month=request.month,
            location=location,
            operator_id=operator_id,
            operator_name=operator_name,
        )

    def is_period_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
    ) -> bool:
        return self.calc_log_service.is_period_processing(
            db, year=year, month=month, location=location.strip()
        )

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        message: str,
        detail_text: str | None = None,
    ) -> None:
        self.calc_log_service.mark_failed(
            db, log_id=log_id, message=message, detail_text=detail_text
        )

    def calculate(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
        progress_callback: ProgressCallback | None = None,
        *,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
        started_at: datetime | None = None,
        current_user: UserVO,
    ) -> SteelPriceCalcResult:
        deps = self._deps
        progress = ProgressNotifier(progress_callback)
        ctx = prepare_calc_run(
            request,
            progress,
            calc_batch_id=calc_batch_id,
            started_at=started_at,
        )
        SteelPricePipeline(deps).run(db, ctx, current_user, progress)
        return persist_calc_result(db, deps, ctx=ctx, log_id=log_id, progress=progress)

    def list_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[SteelPriceCalcLogVO], int]:
        return self.calc_log_service.list_logs(
            db,
            year=year,
            month=month,
            location=location,
            page=page,
            size=size,
        )

    def get_log(self, db: Session, log_id: int) -> SteelPriceCalcLogVO:
        return self.calc_log_service.get_log(db, log_id)

    def delete_log(self, db: Session, log_id: int) -> None:
        self.calc_log_service.delete_log(db, log_id)

    def delete_all_logs(self, db: Session) -> DeletedCountVO:
        return self.calc_log_service.delete_all_logs(db)

    @staticmethod
    def _to_result_vo(result: SteelPriceCalcResult) -> SteelPriceCalcResultVO:
        return SteelPriceCalcResultVO.model_validate(result)

    def start_calc(
        self,
        db: Session,
        dto: SteelPriceCalcDTO,
        current_user: UserVO,
    ) -> AsyncTaskAcceptedVO:
        location = (dto.location or "").strip()
        if not location:
            raise BusinessException("计算钢价必须指定生产基地")
        location = LocationService().require_enabled(db, location)
        request = SteelPriceCalcRequest(
            year=dto.year,
            month=dto.month,
            location=location,
        )
        assert_steel_calc_thickness(db, request)
        lock_log = self.begin_processing(
            db,
            request,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
        started_at = lock_log.started_at
        log_id = lock_log.id
        calc_batch_id = lock_log.calc_batch_id
        async_task_service = AsyncTaskService()
        task = async_task_service.create_task(
            task_type=TASK_TYPE_STEEL_PRICE_CALC,
            message="已提交计算队列",
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )

        def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            result = self.calculate(
                worker_db,
                request,
                progress_callback=on_progress,
                log_id=log_id,
                calc_batch_id=calc_batch_id,
                started_at=started_at,
                current_user=current_user,
            )
            result_vo = self._to_result_vo(result)
            label = calc_status_label(result.status)
            return outcome_from_calc_status(
                result.status,
                failed_message=(
                    f"计算失败：新增 {result.created_count}，"
                    f"更新 {result.updated_count}，失败 {result.failed_count}"
                ),
                completed_message=(
                    f"计算{label}：新增 {result.created_count}，"
                    f"更新 {result.updated_count}，失败 {result.failed_count}"
                ),
                result=result_vo.model_dump(),
            )

        def on_crash(worker_db: Session, error: BaseException) -> None:
            self.mark_log_failed(
                worker_db,
                log_id=log_id,
                message=str(error),
                detail_text=f"计算异常: {error}",
            )

        async_task_service.submit_session_worker(
            task.task_id,
            start_message="后台开始计算...",
            work=work,
            on_crash=on_crash,
            crash_message=lambda error: f"计算异常: {error}",
        )
        return AsyncTaskAcceptedVO(task_id=task.task_id)
