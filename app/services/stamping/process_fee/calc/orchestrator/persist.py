"""核算收尾：拼汇总 VO、落库、写计算日志。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.common.timezone import now
from app.schemas.dto.stamping_process_fee_dto import (
    ProcessFeeCalcLogPatch,
    StampingProcessFeeCalcDTO,
)
from app.schemas.vo.stamping_process_fee_vo import StampingProcessFeeCalcResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.process_fee.calc.constants import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
)
from app.services.stamping.process_fee.calc.orchestrator.batch_engine import BatchCalcOutcome
from app.services.stamping.process_fee.calc.orchestrator.deps import ProcessFeeCalcDeps
from app.services.stamping.process_fee.calc.orchestrator.prep import CalcPrepContext
from app.services.stamping.process_fee.calc.orchestrator.progress import ProgressNotifier


def persist_calc_result(
    db: Session,
    deps: ProcessFeeCalcDeps,
    *,
    dto: StampingProcessFeeCalcDTO,
    ctx: CalcPrepContext,
    batch: BatchCalcOutcome,
    current_user: UserVO,
    log_id: int | None,
    calc_batch_id: str | None,
    progress: ProgressNotifier,
) -> StampingProcessFeeCalcResultVO:
    progress.report(92, "写入加工费结果...")
    if batch.upsert_rows:
        deps.fee_repo.bulk_upsert(db, batch.upsert_rows)

    if batch.failed_items and batch.success_count:
        status = STATUS_PARTIAL
    elif batch.failed_items and not batch.success_count:
        status = STATUS_FAILED
    else:
        status = STATUS_SUCCESS

    detail_lines = list(ctx.detail_lines)
    detail_lines.append(
        f"成功 {batch.success_count}，失败 {len(batch.failed_items)}，"
        f"零价 {batch.zero_fee_count}，跳过已审 {batch.skipped_approved_count}"
    )
    if batch.zero_fee_count:
        detail_lines.append("提醒：存在计算价为 0 的零件，请到列表核对或录入其它费用")
    for item in batch.failed_items[:20]:
        detail_lines.append(f"失败 {item.part_number} {item.process_seq or ''}: {item.reason}")

    finished_at = now()
    result = StampingProcessFeeCalcResultVO(
        year=dto.year,
        location=ctx.location,
        stamping_supplier=ctx.supplier,
        vehicle_model=dto.vehicle_model,
        version=dto.version,
        calc_batch_id=calc_batch_id,
        log_id=log_id,
        status=status,
        total_parts=len(ctx.parts),
        success_count=batch.success_count,
        failed_count=len(batch.failed_items),
        zero_fee_count=batch.zero_fee_count,
        skipped_approved_count=batch.skipped_approved_count,
        failed_items=batch.failed_items[:50],
        zero_fee_items=batch.zero_fee_items,
        detail_text="\n".join(detail_lines),
        started_at=ctx.started_at.isoformat(timespec="seconds"),
        finished_at=finished_at.isoformat(timespec="seconds"),
    )

    if log_id is not None:
        deps.calc_log_service.calc_log_repo.update(
            db,
            log_id,
            ProcessFeeCalcLogPatch(
                status=status,
                total_parts=result.total_parts,
                success_count=result.success_count,
                failed_count=result.failed_count,
                zero_fee_count=result.zero_fee_count,
                skipped_approved_count=result.skipped_approved_count,
                detail_text=result.detail_text,
                finished_at=finished_at,
                updated_by=display_name(current_user) or None,
            ),
        )
        db.commit()
    else:
        db.commit()
        deps.calc_log_service.persist(
            db,
            result=result,
            operator_name=display_name(current_user) or "系统",
        )

    progress.report(100, "计算完成")
    return result
