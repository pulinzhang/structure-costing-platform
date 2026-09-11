"""核算收尾：提交事务并写计算日志。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.schemas.vo.assembly_cost_vo import AssemblyCostCalcResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.costing.assembly_cost.calc.calc_log_service import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
)
from app.services.costing.assembly_cost.calc.orchestrator.batch_engine import BatchCalcOutcome
from app.services.costing.assembly_cost.calc.orchestrator.deps import AssemblyCalcDeps
from app.services.costing.assembly_cost.calc.orchestrator.prep import CalcPrepContext
from app.services.costing.assembly_cost.calc.orchestrator.progress import ProgressNotifier


def _result_message(batch: BatchCalcOutcome) -> str:
    return (
        f"成功 {batch.ok_n}，部分成功 {batch.partial_n}，"
        f"失败 {batch.failed_n}，跳过 {batch.skipped}"
    )


def persist_calc_result(
    db: Session,
    deps: AssemblyCalcDeps,
    *,
    ctx: CalcPrepContext,
    batch: BatchCalcOutcome,
    current_user: UserVO,
    log_id: int | None,
    progress: ProgressNotifier,
) -> AssemblyCostCalcResultVO:
    db.commit()

    if batch.failed_n > 0 and batch.ok_n == 0 and batch.partial_n == 0:
        status = STATUS_FAILED
    elif batch.partial_n > 0 or batch.failed_n > 0:
        status = STATUS_PARTIAL
    else:
        status = STATUS_SUCCESS
    message = _result_message(batch)
    detail_text = ctx.log_builder.build_text()
    detail_json = ctx.log_builder.build_json()
    if log_id is not None:
        deps.calc_log_service.finalize(
            db,
            log_id=log_id,
            status=status,
            message=message,
            subject_total=len(ctx.subjects),
            ok_count=batch.ok_n,
            partial_count=batch.partial_n,
            failed_count=batch.failed_n,
            skipped_approved_count=batch.skipped,
            detail_text=detail_text,
            detail_json=detail_json,
        )
    else:
        deps.calc_log_service.persist(
            db,
            year=ctx.year,
            month=ctx.month,
            location=ctx.location,
            vehicle_model=ctx.vehicle_model,
            bom_version=ctx.bom_version,
            status=status,
            message=message,
            subject_total=len(ctx.subjects),
            ok_count=batch.ok_n,
            partial_count=batch.partial_n,
            failed_count=batch.failed_n,
            skipped_approved_count=batch.skipped,
            detail_text=detail_text,
            detail_json=detail_json,
            operator_id=current_user.id,
            operator_name=display_name(current_user),
        )
    progress.report(100, message)
    return AssemblyCostCalcResultVO(
        status=status,
        created_count=batch.created,
        updated_count=batch.updated,
        skipped_approved_count=batch.skipped,
        ok_count=batch.ok_n,
        partial_count=batch.partial_n,
        failed_count=batch.failed_n,
        message=message,
        detail_text=detail_text,
    )
