"""核算收尾：写钢价过程日志。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.common.duration import duration_seconds
from app.common.timezone import now
from app.services.costing.steel_price.calc.models import SteelPriceCalcResult
from app.services.costing.steel_price.calc.orchestrator.deps import SteelPriceCalcDeps
from app.services.costing.steel_price.calc.orchestrator.prep import CalcPrepContext
from app.services.costing.steel_price.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.steel_price.calc.status import STATUS_FAILED


def persist_calc_result(
    db: Session,
    deps: SteelPriceCalcDeps,
    *,
    ctx: CalcPrepContext,
    log_id: int | None,
    progress: ProgressNotifier,
) -> SteelPriceCalcResult:
    result = ctx.result
    finished_at = now()
    result.finished_at = finished_at.isoformat(timespec="seconds")
    if result.status != STATUS_FAILED:
        ctx.log_builder.line(f"结束时间: {result.finished_at}")
        elapsed = duration_seconds(ctx.started_at, finished_at)
        ctx.log_builder.line(f"耗时: {elapsed} 秒" if elapsed is not None else "耗时: -")
    result.detail_text = ctx.log_builder.build()
    result.log_id = _persist_log(
        db,
        deps,
        result,
        finished_at,
        log_id=log_id,
        persist_log_started_at=ctx.persist_log_started_at,
    )
    if result.status == STATUS_FAILED:
        progress.report(100, f"计算失败: {ctx.error_message or ''}")
    else:
        progress.report(100, f"计算完成：状态 {result.status}")
    return result


def _persist_log(
    db: Session,
    deps: SteelPriceCalcDeps,
    result_obj: SteelPriceCalcResult,
    finished: datetime,
    *,
    log_id: int | None,
    persist_log_started_at: datetime | None,
) -> int | None:
    if log_id is not None:
        return deps.calc_log_service.finalize(
            db,
            log_id=log_id,
            result=result_obj,
            finished_at=finished,
        )
    return deps.calc_log_service.persist(
        db,
        result=result_obj,
        started_at=persist_log_started_at or finished,
        finished_at=finished,
    )
