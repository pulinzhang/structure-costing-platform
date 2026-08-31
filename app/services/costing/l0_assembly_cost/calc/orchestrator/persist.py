"""核算收尾：提交事务并写计算日志。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.vo.l0_assembly_cost_vo import L0AssemblyCostCalcResultVO
from app.services.costing.l0_assembly_cost.calc.calc_log_service import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
)
from app.services.costing.l0_assembly_cost.calc.orchestrator.batch_engine import BatchCalcOutcome
from app.services.costing.l0_assembly_cost.calc.orchestrator.deps import L0AssemblyCalcDeps
from app.services.costing.l0_assembly_cost.calc.orchestrator.prep import CalcPrepContext
from app.services.costing.l0_assembly_cost.calc.orchestrator.progress import ProgressNotifier


def persist_calc_result(
    db: Session,
    deps: L0AssemblyCalcDeps,
    *,
    ctx: CalcPrepContext,
    batch: BatchCalcOutcome,
    log_id: int | None,
    progress: ProgressNotifier,
) -> L0AssemblyCostCalcResultVO:
    db.commit()

    if batch.failed_n > 0 and batch.ok_n == 0 and batch.partial_n == 0:
        status = STATUS_FAILED
    elif batch.partial_n > 0 or batch.failed_n > 0:
        status = STATUS_PARTIAL
    else:
        status = STATUS_SUCCESS
    message = (
        f"新增 {batch.created}，更新 {batch.updated}，跳过已审 {batch.skipped}，"
        f"ok {batch.ok_n}，partial {batch.partial_n}，失败 {batch.failed_n}"
    )
    if log_id is not None:
        deps.calc_log_service.finalize(
            db,
            log_id=log_id,
            status=status,
            message=message,
            l0_total=len(ctx.l0_nodes),
            ok_count=batch.ok_n,
            partial_count=batch.partial_n,
            failed_count=batch.failed_n,
            skipped_approved_count=batch.skipped,
        )
    progress.report(100, message)
    return L0AssemblyCostCalcResultVO(
        status=status,
        created_count=batch.created,
        updated_count=batch.updated,
        skipped_approved_count=batch.skipped,
        ok_count=batch.ok_n,
        partial_count=batch.partial_n,
        failed_count=batch.failed_n,
        message=message,
    )
