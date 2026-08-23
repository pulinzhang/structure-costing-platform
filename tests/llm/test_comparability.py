# -*- coding: utf-8 -*-
"""可比口径动态校验单测。"""

from __future__ import annotations

from decimal import Decimal

from app.repositories.llm.cost_analysis_repository import L0PartPeriodRow
from app.services.llm.analysis.comparability import resolve_runtime_comparability
from app.services.llm.query.comparison_basis import default_comparison_basis


def _row(*, part_number: str, bom_version: str, month: int) -> L0PartPeriodRow:
    return L0PartPeriodRow(
        year=2026,
        month=month,
        part_number=part_number,
        part_name="测试件",
        grand_total=Decimal("100"),
        total_amount=Decimal("90"),
        calc_status="ok",
        missing_leaf_count=0,
        calc_message=None,
        stamping_amount=Decimal("0"),
        purchased_amount=Decimal("0"),
        bundle_amount=Decimal("0"),
        welding_amount=Decimal("0"),
        welding_other_fee=Decimal("0"),
        indirect_amount=Decimal("10"),
        bom_version=bom_version,
    )


def test_bom_drift_marks_loose() -> None:
    basis = default_comparison_basis(same_bom_version=True)
    rows = [
        _row(part_number="501006875AA", bom_version="V1", month=1),
        _row(part_number="501006875AA", bom_version="V2", month=2),
    ]
    comparability, note = resolve_runtime_comparability(basis=basis, part_rows=rows)
    assert comparability == "loose"
    assert note is not None
    assert "BOM" in note
