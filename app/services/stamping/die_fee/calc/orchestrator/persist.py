"""核算收尾：清未审旧结果、落库、写计算日志。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.common.timezone import now
from app.schemas.dto.stamping_die_fee_dto import DieFeeCalcLogPatch, StampingDieFeeCalcDTO
from app.schemas.vo.stamping_die_fee_vo import StampingDieFeeCalcResultVO
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.die_fee.calc.constants import ALL_SUPPLIERS_LOCK, STATUS_SUCCESS
from app.services.stamping.die_fee.calc.orchestrator.batch_engine import BatchCalcOutcome
from app.services.stamping.die_fee.calc.orchestrator.deps import DieFeeCalcDeps
from app.services.stamping.die_fee.calc.orchestrator.missing_die_number import (
    format_missing_die_number_section,
)
from app.services.stamping.die_fee.calc.orchestrator.prep import CalcPrepContext
from app.services.stamping.die_fee.calc.orchestrator.progress import ProgressNotifier


def persist_calc_result(
    db: Session,
    deps: DieFeeCalcDeps,
    *,
    dto: StampingDieFeeCalcDTO,
    ctx: CalcPrepContext,
    batch: BatchCalcOutcome,
    current_user: UserVO,
    log_id: int | None,
    calc_batch_id: str | None,
    progress: ProgressNotifier,
) -> StampingDieFeeCalcResultVO:
    progress.report(25, "清除未审核旧结果...")
    deps.fee_repo.delete_all_by_scope(
        db,
        year=dto.year,
        location=dto.location,
        vehicle_model=dto.vehicle_model,
        stamping_supplier=None,
        version=dto.version,
    )
    for payload in batch.insert_rows:
        deps.fee_repo.insert_with_items(db, payload)

    detail_lines = list(ctx.detail_lines)
    detail_lines.append(
        f"布点（本批落库范围）{len(ctx.persist_parts)} 件，共模扫描 {len(ctx.parts)} 件"
    )
    detail_lines.append(
        f"入库 {batch.success_count}，跳过（无模具信息或系统费≤0）{batch.skipped_no_die_count}"
    )
    if batch.success_count == 0 and batch.skipped_no_die_count:
        detail_lines.append(
            "全部未入库：布点工序没有有效预估重量，也无法按共模继承外形。"
            "请确认上传的是含模具尺寸/重量的布点清单，而不是工艺确认表"
        )
    hint_section = format_missing_die_number_section(batch.missing_die_number_hints)
    if hint_section:
        detail_lines.append(hint_section)
    finished_at = now()
    result = StampingDieFeeCalcResultVO(
        year=dto.year,
        location=dto.location,
        vehicle_model=dto.vehicle_model,
        stamping_supplier=ALL_SUPPLIERS_LOCK,
        version=dto.version,
        calc_batch_id=calc_batch_id,
        log_id=log_id,
        status=STATUS_SUCCESS,
        total_parts=len(ctx.persist_parts),
        success_count=batch.success_count,
        skipped_no_die_count=batch.skipped_no_die_count,
        failed_count=0,
        missing_die_number_count=len(batch.missing_die_number_hints),
        missing_die_number_hints=batch.missing_die_number_hints[:30],
        detail_text="\n".join(detail_lines),
        started_at=ctx.started_at.isoformat(timespec="seconds"),
        finished_at=finished_at.isoformat(timespec="seconds"),
    )
    if log_id is not None:
        deps.calc_log_service.calc_log_repo.update(
            db,
            log_id,
            DieFeeCalcLogPatch(
                status=STATUS_SUCCESS,
                total_parts=result.total_parts,
                success_count=result.success_count,
                skipped_no_die_count=result.skipped_no_die_count,
                failed_count=0,
                detail_text=result.detail_text,
                finished_at=finished_at,
                updated_by=display_name(current_user) or None,
            ),
        )
    db.commit()
    progress.report(100, "计算完成")
    return result
