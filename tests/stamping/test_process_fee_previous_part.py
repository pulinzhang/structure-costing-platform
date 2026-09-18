"""共用件按零件序号减 1 继承吨位，不按 id-1。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from app.services.stamping.process_fee.calc.constants import TONNAGE_SOURCE_INHERITED
from app.services.stamping.process_fee.calc.models import (
    ProcessTonnageResolveResult,
    TonnageRateInfo,
)
from app.services.stamping.process_fee.calc.part_calculator import PartFeeCalculator
from app.services.stamping.process_fee.calc.previous_part import PreviousPartIndex
from app.services.stamping.process_fee.calc.tonnage_resolver import TonnageResolver


def _process(
    *,
    seq: str,
    code: str,
    tonnage: int | None,
    order: int = 1,
    process_id: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=process_id,
        process_seq=seq,
        process_order=order,
        process_code=code,
        tonnage=tonnage,
        cost_ratio=Decimal("0.50"),
        remark=None,
    )


def _part(
    *,
    part_id: int,
    seq_no: int,
    number: str,
    processes: list[SimpleNamespace],
    effective_year: int = 2020,
    effective_month: int = 1,
    expiry_year: int | None = None,
    expiry_month: int | None = None,
    process_method: str = "左右合并",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=part_id,
        seq_no=seq_no,
        part_number=number,
        part_name=number,
        location="青岛",
        vehicle_model="T28",
        stamping_supplier="烟台海众",
        process_method=process_method,
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        is_scrap_byproduct=False,
        is_tailor_welded=False,
        processes=processes,
    )


def test_inherit_uses_seq_no_minus_one_not_id() -> None:
    left = _part(
        part_id=10,
        seq_no=5,
        number="LEFT",
        processes=[_process(seq="OP10", code="DR", tonnage=400, process_id=1)],
    )
    stranger = _part(
        part_id=998,
        seq_no=100,
        number="STRANGER",
        processes=[_process(seq="OP10", code="DR", tonnage=800, process_id=2)],
        process_method="单件",
    )
    right = _part(
        part_id=999,
        seq_no=6,
        number="RIGHT",
        processes=[_process(seq="OP10", code="共用", tonnage=None, process_id=3)],
    )
    index = PreviousPartIndex.from_parts([left, stranger, right])
    resolved = TonnageResolver().resolve(right, right.processes[0], index)
    assert isinstance(resolved, ProcessTonnageResolveResult)
    assert resolved.source == TONNAGE_SOURCE_INHERITED
    assert resolved.tonnage == 400
    assert resolved.inherited_from_part_number == "LEFT"
    assert resolved.inherited_from_process_seq == "OP10"


def test_year_overlap_picks_same_generation_by_period() -> None:
    old_left = _part(
        part_id=1,
        seq_no=5,
        number="LEFT-AA",
        processes=[_process(seq="OP10", code="DR", tonnage=200, process_id=11)],
        expiry_year=2025,
        expiry_month=7,
    )
    new_left = _part(
        part_id=5000,
        seq_no=5,
        number="LEFT-AB",
        processes=[_process(seq="OP10", code="DR", tonnage=400, process_id=21)],
        effective_year=2025,
        effective_month=8,
    )
    new_right = _part(
        part_id=5001,
        seq_no=6,
        number="RIGHT-AB",
        processes=[_process(seq="OP10", code="共用", tonnage=None, process_id=31)],
        effective_year=2025,
        effective_month=8,
    )
    index = PreviousPartIndex.from_parts([old_left, new_left, new_right])
    resolved = TonnageResolver().resolve(new_right, new_right.processes[0], index)
    assert isinstance(resolved, ProcessTonnageResolveResult)
    assert resolved.tonnage == 400
    assert resolved.inherited_from_part_number == "LEFT-AB"


def test_missing_previous_seq_mentions_seq_not_id() -> None:
    right = _part(
        part_id=999,
        seq_no=6,
        number="RIGHT",
        processes=[_process(seq="OP10", code="共用", tonnage=None)],
    )
    resolved = TonnageResolver().resolve(right, right.processes[0], PreviousPartIndex())
    assert isinstance(resolved, str)
    assert "序号 5" in resolved
    assert "id-1" not in resolved


def test_part_fee_inherits_after_id_gap() -> None:
    left = _part(
        part_id=10,
        seq_no=5,
        number="LEFT",
        processes=[_process(seq="OP10", code="DR", tonnage=400, process_id=1)],
    )
    right = _part(
        part_id=999,
        seq_no=6,
        number="RIGHT",
        processes=[_process(seq="OP10", code="共用", tonnage=None, process_id=3)],
    )
    rate_map = {
        400: TonnageRateInfo(price_per_stroke=Decimal("1.000"), tonnage_price_id=1),
    }
    result = PartFeeCalculator().calc_part_fee(
        right,
        rate_map,
        2026,
        PreviousPartIndex.from_parts([left, right]),
    )
    assert isinstance(result, tuple)
    total, process_count, items = result
    assert process_count == 1
    assert items[0].resolved_tonnage == 400
    assert items[0].inherited_from_part_number == "LEFT"
    assert total == Decimal("0.500")
