"""
指挥家：只挥棒，不拉琴。违反指挥家宪法（orchestrator-constitution）即不合格。

成品月核价 — 计算编排器（预备 → 引擎 → 收尾）

计算链：
  1. prepare_calc_run                   — BOM / 上游价表
  2. BatchCalculationEngine.run         — 逐 L0 rollup
  3. persist_calc_result                — 提交并写日志
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.schemas.dto.l0_assembly_cost_dto import L0AssemblyCostCalcDTO
from app.schemas.vo.l0_assembly_cost_vo import (
    L0AssemblyCostCalcReadyVO,
    L0AssemblyCostCalcResultVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.l0_assembly_cost.calc.orchestrator.batch_engine import (
    BatchCalculationEngine,
)
from app.services.costing.l0_assembly_cost.calc.orchestrator.deps import (
    L0AssemblyCalcDeps,
    build_l0_assembly_calc_deps,
)
from app.services.costing.l0_assembly_cost.calc.orchestrator.persist import persist_calc_result
from app.services.costing.l0_assembly_cost.calc.orchestrator.prep import prepare_calc_run
from app.services.costing.l0_assembly_cost.calc.orchestrator.progress import (
    ProgressCallback,
    ProgressNotifier,
)
from app.services.costing.l0_assembly_cost.calc.orchestrator.ready import collect_calc_ready

logger = logging.getLogger("service.costing.l0_assembly_cost.calc")


class L0AssemblyCostCalcOrchestrator:
    """成品月核价计算编排。"""

    def __init__(self, deps: L0AssemblyCalcDeps | None = None) -> None:
        self._deps = deps or build_l0_assembly_calc_deps()
        self.calc_log_service = self._deps.calc_log_service

    def get_calc_ready(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> L0AssemblyCostCalcReadyVO:
        return collect_calc_ready(
            db,
            self._deps,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def calculate(
        self,
        db: Session,
        dto: L0AssemblyCostCalcDTO,
        *,
        current_user: UserVO,
        progress_callback: ProgressCallback | None = None,
        log_id: int | None = None,
        calc_batch_id: str | None = None,
    ) -> L0AssemblyCostCalcResultVO:
        deps = self._deps
        progress = ProgressNotifier(progress_callback)

        def release_lock_on_error(exc: BaseException) -> None:
            if log_id is None:
                return
            try:
                deps.calc_log_service.mark_log_failed(
                    db, log_id=log_id, detail_text=f"计算失败: {exc}"
                )
            except Exception:
                logger.exception("释放成品核价计算锁失败: log_id=%s", log_id)

        try:
            ctx = prepare_calc_run(db, deps, dto, progress)
            batch = BatchCalculationEngine(deps).run(
                db,
                ctx=ctx,
                current_user=current_user,
                calc_batch_id=calc_batch_id,
                progress=progress,
            )
            return persist_calc_result(
                db,
                deps,
                ctx=ctx,
                batch=batch,
                log_id=log_id,
                progress=progress,
            )
        except Exception as exc:
            logger.exception("成品核价整批失败: %s", exc)
            release_lock_on_error(exc)
            raise
