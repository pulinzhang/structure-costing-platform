"""批量焊接费引擎：逐 L0 计费与落库载荷。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, audit_create, audit_update
from app.schemas.dto.bom_welding_fee_dto import BomWeldingFeeUpsertPayload
from app.schemas.vo.user_vo import UserVO
from app.services.bom.welding_fee.calc.orchestrator.deps import WeldingFeeCalcDeps
from app.services.bom.welding_fee.calc.orchestrator.node_fee import CALC_FAILED, calc_node_fee
from app.services.bom.welding_fee.calc.orchestrator.prep import CalcPrepContext
from app.services.bom.welding_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.bom.welding_fee.calc.staff_report import FailedNodeNote, human_failed_reason
from app.services.bom.welding_fee.fee_math import resolve_final_welding_fee


@dataclass(slots=True)
class BatchCalcOutcome:
    upsert_rows: list[BomWeldingFeeUpsertPayload] = field(default_factory=list)
    skipped_approved_count: int = 0
    failed_count: int = 0
    missing_price_total: int = 0
    failed_notes: list[FailedNodeNote] = field(default_factory=list)


class BatchCalculationEngine:
    def __init__(self, deps: WeldingFeeCalcDeps) -> None:
        self._deps = deps

    def run(
        self,
        db: Session,
        *,
        ctx: CalcPrepContext,
        current_user: UserVO,
        calc_batch_id: str | None,
        progress: ProgressNotifier,
    ) -> BatchCalcOutcome:
        outcome = BatchCalcOutcome()
        audit = audit_create(current_user)
        update_audit = audit_update(current_user)
        total = len(ctx.nodes)

        for index, node in enumerate(ctx.nodes, start=1):
            existing = self._deps.fee_repo.get_by_business_key(
                db,
                year=ctx.year,
                location=ctx.location,
                vehicle_model=ctx.vehicle_model,
                bom_version=ctx.bom_version,
                source_breakdown_node_id=node.id,
            )
            if existing is not None and existing.audit_status == AUDIT_APPROVED:
                outcome.skipped_approved_count += 1
                progress.tick_parts(index, total)
                continue

            parts = calc_node_fee(node, ctx.price_map)
            outcome.missing_price_total += parts.missing_price_count
            calc_message = parts.calc_message
            if parts.calc_status == CALC_FAILED:
                outcome.failed_count += 1
                outcome.failed_notes.append(
                    FailedNodeNote(
                        level=int(node.level),
                        part_number=node.part_number,
                        part_name=node.part_name,
                        weld_info_raw=(node.weld_info_raw or "").strip() or None,
                        calc_message=parts.calc_message,
                        excel_row=getattr(node, "excel_row", None),
                        excel_filename=ctx.source_excel_filename,
                        sheet_name=ctx.source_sheet_name,
                    )
                )
                calc_message = human_failed_reason(parts.calc_message)

            other_fee = existing.other_fee if existing else None
            final_fee = resolve_final_welding_fee(
                parts.total_welding_fee,
                other_fee,
            )

            outcome.upsert_rows.append(
                BomWeldingFeeUpsertPayload(
                    year=ctx.year,
                    location=ctx.location,
                    vehicle_model=ctx.vehicle_model,
                    bom_version=ctx.bom_version,
                    level=int(node.level),
                    source_breakdown_node_id=node.id,
                    part_number=node.part_number,
                    part_name=node.part_name,
                    customer_name=node.customer_name,
                    weld_info_raw=(node.weld_info_raw or "").strip() or None,
                    process_line_count=parts.process_line_count,
                    matched_line_count=parts.matched_line_count,
                    missing_price_count=parts.missing_price_count,
                    total_welding_fee=parts.total_welding_fee,
                    final_welding_fee=final_fee,
                    calc_batch_id=calc_batch_id,
                    calc_status=parts.calc_status,
                    calc_message=calc_message,
                    audit_status=AUDIT_PENDING,
                    updated_by=(update_audit["updated_by"] if existing else audit["updated_by"]),
                    created_by=None if existing else audit["created_by"],
                    items=parts.items,
                )
            )
            progress.tick_parts(index, total)

        return outcome
