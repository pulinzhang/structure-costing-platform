"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

冲压零件价格核算编排器（预备 → 引擎 → 收尾）

计算链：
  1. prepare_calc_run                   — 就绪 / 废料 / 零件
  2. BatchCalculationEngine.run         — 逐件核价
  3. persist_calc_result                — 格式化 VO 并落库
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.costing import StampingPartCostCalcLog
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.schemas.vo.stamping_part_cost_vo import (
    StampingPartCostCalcReadyVO,
    StampingPartCostCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.stamping_part_cost.calc.models import ProgressCallback
from app.services.costing.stamping_part_cost.calc.orchestrator.batch_engine import (
    BatchCalculationEngine,
)
from app.services.costing.stamping_part_cost.calc.orchestrator.deps import (
    PartCostCalcDeps,
    build_part_cost_calc_deps,
)
from app.services.costing.stamping_part_cost.calc.orchestrator.persist import persist_calc_result
from app.services.costing.stamping_part_cost.calc.orchestrator.prep import prepare_calc_run
from app.services.costing.stamping_part_cost.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.stamping_part_cost.calc.orchestrator.ready import collect_calc_ready


class StampingPartCostCalcOrchestrator:
    """冲压零件价格核算编排器。"""

    def __init__(self, deps: PartCostCalcDeps | None = None) -> None:
        self._deps = deps or build_part_cost_calc_deps()
        self.calc_log_service = self._deps.calc_log_service

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        month: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> StampingPartCostCalcReadyVO:
        return collect_calc_ready(
            db,
            self._deps,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
        )

    def begin_processing(
        self,
        db: Session,
        dto: StampingPartCostCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> StampingPartCostCalcLog:
        return self._deps.calc_log_service.begin_processing(
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
        self._deps.calc_log_service.mark_log_failed(db, log_id=log_id, detail_text=detail_text)

    def calculate(
        self,
        db: Session,
        dto: StampingPartCostCalcDTO,
        current_user: UserVO,
        *,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> StampingPartCostCalcResultVO:
        progress = ProgressNotifier(progress_callback)
        ctx = prepare_calc_run(db, self._deps, dto, progress)
        batch = BatchCalculationEngine(self._deps, ctx.rates).run(
            db,
            ctx=ctx,
            dto=dto,
            current_user=current_user,
            calc_batch_id=calc_batch_id,
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
