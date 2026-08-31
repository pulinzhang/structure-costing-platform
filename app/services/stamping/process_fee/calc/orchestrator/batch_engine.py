"""批量加工费引擎：逐件计费与落库载荷，不负责阶段文案与写库。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, audit_create, audit_update
from app.models.stamping import StampingPart
from app.schemas.dto.stamping_process_fee_dto import (
    ProcessFeeItemPayload,
    ProcessFeeUpsertPayload,
    StampingProcessFeeCalcDTO,
)
from app.schemas.vo.stamping_process_fee_vo import StampingProcessFeeFailedItemVO
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.process_fee.calc.orchestrator.deps import ProcessFeeCalcDeps
from app.services.stamping.process_fee.calc.orchestrator.prep import CalcPrepContext
from app.services.stamping.process_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.stamping.process_fee.calc.part_calculator import PartFeeCalculator
from app.services.stamping.process_fee.calc.snapshot import part_snapshot
from app.services.stamping.process_fee.calc.tailor_weld_calculator import (
    TailorWeldFeeCalculator,
)
from app.services.stamping.process_fee.fee_math import resolve_final_fee


@dataclass(slots=True)
class BatchCalcOutcome:
    upsert_rows: list[ProcessFeeUpsertPayload] = field(default_factory=list)
    failed_items: list[StampingProcessFeeFailedItemVO] = field(default_factory=list)
    zero_fee_items: list[StampingProcessFeeFailedItemVO] = field(default_factory=list)
    success_count: int = 0
    zero_fee_count: int = 0
    skipped_approved_count: int = 0


class BatchCalculationEngine:
    def __init__(self, deps: ProcessFeeCalcDeps) -> None:
        self._deps = deps

    def run(
        self,
        db: Session,
        *,
        ctx: CalcPrepContext,
        dto: StampingProcessFeeCalcDTO,
        current_user: UserVO,
        progress: ProgressNotifier,
    ) -> BatchCalcOutcome:
        outcome = BatchCalcOutcome()
        audit = audit_create(current_user)
        update_audit = audit_update(current_user)
        prev_part_cache: dict[int, StampingPart | None] = {}
        total = len(ctx.parts)

        for index, part in enumerate(ctx.parts, start=1):
            self._process_part(
                db,
                part=part,
                dto=dto,
                ctx=ctx,
                existing_created_by=audit["created_by"],
                existing_updated_by=update_audit["updated_by"],
                new_updated_by=audit["updated_by"],
                prev_part_cache=prev_part_cache,
                outcome=outcome,
            )
            progress.tick_parts(index, total)

        return outcome

    def _select_calculator(self, part: StampingPart) -> PartFeeCalculator | TailorWeldFeeCalculator:
        if part.is_tailor_welded:
            return self._deps.tailor_weld_calculator
        return self._deps.part_calculator

    def _process_part(
        self,
        db: Session,
        *,
        part: StampingPart,
        dto: StampingProcessFeeCalcDTO,
        ctx: CalcPrepContext,
        existing_created_by: str,
        existing_updated_by: str,
        new_updated_by: str,
        prev_part_cache: dict[int, StampingPart | None],
        outcome: BatchCalcOutcome,
    ) -> None:
        existing = self._deps.fee_repo.get_by_business_key(
            db,
            year=dto.year,
            location=part.location,
            stamping_supplier=ctx.supplier,
            vehicle_model=part.vehicle_model,
            version=part.version,
            part_number=part.part_number,
        )
        if existing is not None and existing.audit_status == AUDIT_APPROVED:
            outcome.skipped_approved_count += 1
            return

        fee_or_error = self._select_calculator(part).calc_part_fee(
            db, part, ctx.rate_map, dto.year, prev_part_cache
        )
        other_fee = existing.other_fee if existing else None

        if isinstance(fee_or_error, StampingProcessFeeFailedItemVO):
            outcome.failed_items.append(fee_or_error)
            processing_fee = None
            process_count = len(part.processes or [])
            calc_fail_reason = fee_or_error.reason
            process_items: list[ProcessFeeItemPayload] = []
        else:
            processing_fee, process_count, process_items = fee_or_error
            calc_fail_reason = None
            outcome.success_count += 1
            if processing_fee is not None and Decimal(str(processing_fee)) == 0:
                outcome.zero_fee_count += 1
                if len(outcome.zero_fee_items) < 50:
                    zero_reason = (
                        "拼焊件系统计算不含拼焊费，请到列表录入其它费用"
                        if part.is_tailor_welded
                        else "系统计算加工费为 0，请到列表核对或录入其它费用"
                    )
                    outcome.zero_fee_items.append(
                        StampingProcessFeeFailedItemVO(
                            part_number=part.part_number,
                            part_name=part.part_name,
                            process_seq=None,
                            process_code=None,
                            process_method=None,
                            reason=zero_reason,
                        )
                    )

        final_fee = resolve_final_fee(processing_fee, other_fee)
        outcome.upsert_rows.append(
            ProcessFeeUpsertPayload(
                year=dto.year,
                location=part.location,
                stamping_supplier=ctx.supplier,
                vehicle_model=part.vehicle_model,
                version=part.version,
                snapshot=part_snapshot(part),
                processing_fee=processing_fee,
                process_count=process_count,
                final_processing_fee=final_fee,
                calc_fail_reason=calc_fail_reason,
                audit_status=AUDIT_PENDING,
                created_by=None if existing else existing_created_by,
                updated_by=existing_updated_by if existing else new_updated_by,
                process_items=process_items,
            )
        )
