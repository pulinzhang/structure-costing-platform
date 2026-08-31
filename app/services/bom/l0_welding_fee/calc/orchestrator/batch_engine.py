"""批量焊接费引擎：逐 L0 计费与落库载荷。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, audit_create, audit_update
from app.schemas.dto.bom_l0_welding_fee_dto import BomL0WeldingFeeUpsertPayload
from app.schemas.vo.user_vo import UserVO
from app.services.bom.l0_welding_fee.calc.orchestrator.deps import L0WeldingFeeCalcDeps
from app.services.bom.l0_welding_fee.calc.orchestrator.l0_fee import CALC_FAILED, calc_l0_fee
from app.services.bom.l0_welding_fee.calc.orchestrator.prep import CalcPrepContext
from app.services.bom.l0_welding_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.bom.l0_welding_fee.fee_math import resolve_final_l0_welding_fee


@dataclass(slots=True)
class BatchCalcOutcome:
    upsert_rows: list[BomL0WeldingFeeUpsertPayload] = field(default_factory=list)
    skipped_approved_count: int = 0
    failed_count: int = 0
    missing_price_total: int = 0


class BatchCalculationEngine:
    def __init__(self, deps: L0WeldingFeeCalcDeps) -> None:
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
        total = len(ctx.l0_nodes)

        for index, node in enumerate(ctx.l0_nodes, start=1):
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

            parts = calc_l0_fee(node, ctx.price_map)
            outcome.missing_price_total += parts.missing_price_count
            if parts.calc_status == CALC_FAILED:
                outcome.failed_count += 1

            other_fee = existing.other_fee if existing else None
            final_fee = resolve_final_l0_welding_fee(
                parts.total_l0_welding_fee,
                other_fee,
            )

            outcome.upsert_rows.append(
                BomL0WeldingFeeUpsertPayload(
                    year=ctx.year,
                    location=ctx.location,
                    vehicle_model=ctx.vehicle_model,
                    bom_version=ctx.bom_version,
                    source_breakdown_node_id=node.id,
                    part_number=node.part_number,
                    part_name=node.part_name,
                    customer_name=node.customer_name,
                    weld_info_raw=(node.weld_info_raw or "").strip() or None,
                    process_line_count=parts.process_line_count,
                    matched_line_count=parts.matched_line_count,
                    missing_price_count=parts.missing_price_count,
                    total_l0_welding_fee=parts.total_l0_welding_fee,
                    final_l0_welding_fee=final_fee,
                    calc_batch_id=calc_batch_id,
                    calc_status=parts.calc_status,
                    calc_message=parts.calc_message,
                    audit_status=AUDIT_PENDING,
                    updated_by=(update_audit["updated_by"] if existing else audit["updated_by"]),
                    created_by=None if existing else audit["created_by"],
                    items=parts.items,
                )
            )
            progress.tick_parts(index, total)

        return outcome
