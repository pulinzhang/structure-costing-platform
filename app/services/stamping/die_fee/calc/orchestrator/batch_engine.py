"""批量模具费引擎：共模扫全集，身份命中才生成落库载荷。"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.common.audit import AUDIT_PENDING, audit_create
from app.models.stamping.die import StampingDiePart
from app.schemas.dto.stamping_die_fee_dto import (
    DieFeeInsertPayload,
    DieFeeItemPayload,
    StampingDieFeeCalcDTO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.die_fee.calc.orchestrator.identity import (
    is_scrap_byproduct_die_part,
    matches_part,
)
from app.services.stamping.die_fee.calc.orchestrator.missing_die_number import (
    collect_missing_die_number_hints,
)
from app.services.stamping.die_fee.calc.orchestrator.prep import CalcPrepContext
from app.services.stamping.die_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.stamping.die_fee.calc.part_calculator import DieFeePartCalculator
from app.services.stamping.die_fee.calc.weight_resolver import PreviousWeightIndex
from app.services.stamping.die_fee.rules.fee_math import DieFeeLineResult


@dataclass(slots=True)
class BatchCalcOutcome:
    insert_rows: list[DieFeeInsertPayload] = field(default_factory=list)
    success_count: int = 0
    skipped_no_die_count: int = 0
    missing_die_number_hints: list[str] = field(default_factory=list)


class BatchCalculationEngine:
    def __init__(self, part_calculator: DieFeePartCalculator) -> None:
        self._part_calculator = part_calculator

    def run(
        self,
        *,
        ctx: CalcPrepContext,
        dto: StampingDieFeeCalcDTO,
        current_user: UserVO,
        progress: ProgressNotifier,
    ) -> BatchCalcOutcome:
        outcome = BatchCalcOutcome()
        audit = audit_create(current_user)
        previous_weights = PreviousWeightIndex()
        total = len(ctx.parts)
        price = ctx.price

        for index, part in enumerate(ctx.parts, start=1):
            if is_scrap_byproduct_die_part(part, ctx.scrap_byproduct_keys):
                if matches_part(
                    part,
                    stamping_supplier=None,
                    version=dto.version,
                ):
                    outcome.skipped_no_die_count += 1
                progress.tick_parts(index, total)
                continue
            calculated, previous_weights = self._part_calculator.calc_part(
                part,
                steel_plate_unit_price=price.steel_plate_unit_price,
                progressive_die_unit_price=price.progressive_die_unit_price,
                allocation_qty=price.allocation_qty,
                previous_weights=previous_weights,
            )
            if matches_part(
                part,
                stamping_supplier=None,
                version=dto.version,
            ):
                outcome.missing_die_number_hints.extend(collect_missing_die_number_hints(part))
                if calculated is None:
                    outcome.skipped_no_die_count += 1
                else:
                    outcome.insert_rows.append(
                        _build_insert_payload(
                            dto=dto,
                            part=part,
                            calculated=calculated,
                            allocation_qty=price.allocation_qty,
                            created_by=audit["created_by"],
                            updated_by=audit["updated_by"],
                        )
                    )
                    outcome.success_count += 1
            progress.tick_parts(index, total)

        return outcome


def _build_insert_payload(
    *,
    dto: StampingDieFeeCalcDTO,
    part: StampingDiePart,
    calculated: tuple[Decimal, str, Decimal, list[DieFeeLineResult]],
    allocation_qty: Decimal,
    created_by: str,
    updated_by: str,
) -> DieFeeInsertPayload:
    die_fee, price_kind, unit_price, lines = calculated
    return DieFeeInsertPayload(
        year=dto.year,
        location=part.location,
        vehicle_model=part.vehicle_model,
        stamping_supplier=part.stamping_supplier,
        version=part.version,
        part_number=part.part_number,
        source_die_part_id=part.id,
        seq_no=part.seq_no,
        part_name=part.part_name,
        material=part.material,
        thickness=part.thickness,
        part_weight=part.part_weight,
        die_type=part.die_type,
        die_method=part.die_method,
        production_mode=part.production_mode,
        part_grade=part.part_grade,
        excel_filename=part.excel_filename,
        price_kind=price_kind,
        unit_price=unit_price,
        allocation_qty=allocation_qty,
        die_fee=die_fee,
        adjustment_amount=None,
        final_die_fee=die_fee,
        audit_status=AUDIT_PENDING,
        created_by=created_by,
        updated_by=updated_by,
        items=[
            DieFeeItemPayload(
                source_die_process_id=line.source_die_process_id,
                process_seq=line.process_seq,
                process_order=line.process_order,
                process_code=line.process_code,
                estimated_weight_t=line.estimated_weight_t,
                alloc_ratio=line.alloc_ratio,
                die_sets=line.die_sets,
                unit_price=unit_price,
                allocation_qty=allocation_qty,
                price_kind=price_kind,
                line_die_fee=line.line_die_fee,
                basis_text=line.basis_text,
            )
            for line in lines
        ],
    )
