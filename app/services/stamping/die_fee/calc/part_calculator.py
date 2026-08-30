"""按布点零件计算系统模具费。"""

from __future__ import annotations

from decimal import Decimal

from app.models.stamping.die import StampingDiePart
from app.services.stamping.die_fee.calc.weight_resolver import (
    WEIGHT_SOURCE_INHERITED,
    PreviousWeightIndex,
    index_resolved_weights,
    resolve_part_weights,
)
from app.services.stamping.die_fee.fee_math import (
    PRICE_KIND_PROGRESSIVE,
    DieFeeLineResult,
    ZERO,
    build_line_basis_text,
    calc_line_die_fee,
    resolve_price_kind,
    sum_line_fees,
)


class DieFeePartCalculator:
    def calc_part(
        self,
        part: StampingDiePart,
        *,
        steel_plate_unit_price: Decimal,
        progressive_die_unit_price: Decimal,
        allocation_qty: Decimal,
        previous_weights: PreviousWeightIndex | None = None,
    ) -> tuple[
        tuple[Decimal, str, Decimal, list[DieFeeLineResult]] | None,
        PreviousWeightIndex,
    ]:
        previous = previous_weights or PreviousWeightIndex()
        processes = list(part.processes or [])
        if not processes:
            return None, previous
        resolved = resolve_part_weights(part, previous)
        next_index = index_resolved_weights(part, resolved)
        price_kind = resolve_price_kind(part.production_mode)
        unit_price = (
            progressive_die_unit_price
            if price_kind == PRICE_KIND_PROGRESSIVE
            else steel_plate_unit_price
        )
        lines: list[DieFeeLineResult] = []
        for process in processes:
            seq = (process.process_seq or "").strip()
            weight_info = resolved.get(seq) if seq else None
            weight = weight_info.weight_t if weight_info else None
            line_fee = calc_line_die_fee(
                estimated_weight_t=weight,
                unit_price=unit_price,
                alloc_ratio=process.alloc_ratio,
                allocation_qty=allocation_qty,
            )
            if line_fee is None or weight is None:
                continue
            ratio = process.alloc_ratio if process.alloc_ratio is not None else Decimal("1.00")
            inherited_part = None
            inherited_seq = None
            if weight_info is not None and weight_info.source == WEIGHT_SOURCE_INHERITED:
                inherited_part = weight_info.inherited_from_part_number
                inherited_seq = weight_info.inherited_from_process_seq
            lines.append(
                DieFeeLineResult(
                    process_seq=process.process_seq,
                    process_order=process.process_order,
                    process_code=process.process_code,
                    source_die_process_id=process.id,
                    estimated_weight_t=weight,
                    alloc_ratio=ratio,
                    die_sets=process.die_sets,
                    line_die_fee=line_fee,
                    basis_text=build_line_basis_text(
                        estimated_weight_t=weight,
                        unit_price=unit_price,
                        alloc_ratio=ratio,
                        allocation_qty=allocation_qty,
                        line_die_fee=line_fee,
                        inherited_from_part_number=inherited_part,
                        inherited_from_process_seq=inherited_seq,
                    ),
                )
            )
        if not lines:
            return None, next_index
        die_fee = sum_line_fees([item.line_die_fee for item in lines])
        if die_fee <= ZERO:
            return None, next_index
        return (die_fee, price_kind, unit_price, lines), next_index
