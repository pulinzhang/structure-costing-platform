"""核算收尾：拼汇总 VO、落库、写计算日志。"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.common.timezone import now
from app.schemas.vo.bom_welding_fee_vo import BomWeldingFeeCalcResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.welding_fee.calc.calc_log_service import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_SUCCESS,
)
from app.services.bom.welding_fee.calc.orchestrator.batch_engine import BatchCalcOutcome
from app.services.bom.welding_fee.calc.orchestrator.deps import WeldingFeeCalcDeps
from app.services.bom.welding_fee.calc.orchestrator.prep import CalcPrepContext
from app.services.bom.welding_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.bom.welding_fee.calc.staff_report import format_failed_staff_section

logger = logging.getLogger("service.bom.welding_fee.calc")


def persist_calc_result(
    db: Session,
    deps: WeldingFeeCalcDeps,
    *,
    ctx: CalcPrepContext,
    batch: BatchCalcOutcome,
    current_user: UserVO,
    log_id: int | None,
    calc_batch_id: str | None,
    progress: ProgressNotifier,
) -> BomWeldingFeeCalcResultVO:
    progress.report(92, "写入焊接费结果...")
    created_count = 0
    updated_count = 0
    if batch.upsert_rows:
        _, created_count, updated_count = deps.fee_repo.bulk_upsert(db, batch.upsert_rows)

    if batch.failed_count and (created_count + updated_count - batch.failed_count) > 0:
        status = STATUS_PARTIAL
    elif batch.failed_count and (created_count + updated_count) == batch.failed_count:
        status = STATUS_FAILED
    elif batch.missing_price_total and (created_count + updated_count):
        status = STATUS_PARTIAL
    else:
        status = STATUS_SUCCESS

    detail_lines = list(ctx.detail_lines)
    detail_lines.append(
        f"新增 {created_count}，更新 {updated_count}，"
        f"失败 {batch.failed_count}，缺单价明细 {batch.missing_price_total}，"
        f"跳过已审 {batch.skipped_approved_count}"
    )
    staff_lines = format_failed_staff_section(batch.failed_notes)
    if staff_lines:
        detail_lines.append("")
        detail_lines.extend(staff_lines)

    finished_at = now()
    result = BomWeldingFeeCalcResultVO(
        year=ctx.year,
        location=ctx.location,
        vehicle_model=ctx.vehicle_model,
        bom_version=ctx.bom_version,
        calc_batch_id=calc_batch_id,
        log_id=log_id,
        status=status,
        l0_count=len(ctx.nodes),
        created_count=created_count,
        updated_count=updated_count,
        skipped_approved_count=batch.skipped_approved_count,
        failed_count=batch.failed_count,
        missing_price_count=batch.missing_price_total,
        detail_text="\n".join(detail_lines),
        started_at=ctx.started_at.isoformat(timespec="seconds"),
        finished_at=finished_at.isoformat(timespec="seconds"),
    )

    if log_id is not None:
        deps.calc_log_service.finalize(
            db,
            log_id=log_id,
            data={
                "status": status,
                "l0_count": result.l0_count,
                "created_count": result.created_count,
                "updated_count": result.updated_count,
                "skipped_approved_count": result.skipped_approved_count,
                "failed_count": result.failed_count,
                "missing_price_count": result.missing_price_count,
                "detail_text": result.detail_text,
                "finished_at": finished_at,
                "updated_by": display_name(current_user) or None,
            },
        )
    else:
        db.commit()
        deps.calc_log_service.persist(
            db,
            result=result,
            operator_name=display_name(current_user) or "系统",
        )

    progress.report(100, "计算完成")
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
