"""总成月核价 rollup：间接费行。"""

from __future__ import annotations

from decimal import Decimal

from app.common.measures import PERCENT, PERMILLE
from app.services.costing.assembly_cost.calc.identities import quantize_money
from app.services.costing.assembly_cost.calc.rollup_models import (
    INDIRECT_FINANCE,
    INDIRECT_FIXTURE_ALLOC,
    INDIRECT_GAUGE_ALLOC,
    INDIRECT_LABELS,
    INDIRECT_MANAGEMENT,
    INDIRECT_PRETAX_PROFIT,
    INDIRECT_SCRAP,
    INDIRECT_UNIT_TRANSPORT,
    INDIRECT_WAREHOUSE_BUNDLING,
    RollupAllocationFees,
    RollupFinishedRates,
    RollupIndirectLine,
    RollupPackagingFee,
)


def format_rate_label(base_label: str, rate: Decimal) -> str:
    if rate == 0:
        return base_label
    permille = rate * PERMILLE
    if permille == permille.to_integral_value() and rate < Decimal("0.01"):
        return f"{base_label}（{permille.to_integral_value()}‰）"
    percent = rate * PERCENT
    if percent == percent.to_integral_value():
        return f"{base_label}（{percent.to_integral_value()}%）"
    return f"{base_label}（{percent.normalize()}%）"


def build_indirect_lines(
    *,
    monthly_total: Decimal,
    packaging: RollupPackagingFee | None,
    rates: RollupFinishedRates,
    allocation: RollupAllocationFees | None = None,
) -> list[RollupIndirectLine]:
    transport = Decimal("0")
    bundling = Decimal("0")
    if packaging is not None:
        transport = packaging.unit_transport_fee
        bundling = packaging.warehouse_bundling_fee
    alloc = allocation or RollupAllocationFees()

    lines: list[RollupIndirectLine] = [
        RollupIndirectLine(
            code=INDIRECT_UNIT_TRANSPORT,
            label=INDIRECT_LABELS[INDIRECT_UNIT_TRANSPORT],
            amount=quantize_money(transport),
            sort_no=1,
        ),
        RollupIndirectLine(
            code=INDIRECT_WAREHOUSE_BUNDLING,
            label=INDIRECT_LABELS[INDIRECT_WAREHOUSE_BUNDLING],
            amount=quantize_money(bundling),
            sort_no=2,
        ),
    ]
    rate_items: tuple[tuple[str, Decimal, int], ...] = (
        (INDIRECT_FINANCE, rates.finance_rate, 3),
        (INDIRECT_MANAGEMENT, rates.management_rate, 4),
        (INDIRECT_SCRAP, rates.scrap_rate, 5),
        (INDIRECT_PRETAX_PROFIT, rates.pretax_profit_rate, 6),
    )
    for code, rate, sort_no in rate_items:
        lines.append(
            RollupIndirectLine(
                code=code,
                label=format_rate_label(INDIRECT_LABELS[code], rate),
                amount=quantize_money(monthly_total * rate),
                rate=rate,
                base_amount=monthly_total,
                sort_no=sort_no,
            )
        )
    lines.append(
        RollupIndirectLine(
            code=INDIRECT_GAUGE_ALLOC,
            label=INDIRECT_LABELS[INDIRECT_GAUGE_ALLOC],
            amount=quantize_money(alloc.gauge_alloc_fee),
            sort_no=7,
        )
    )
    lines.append(
        RollupIndirectLine(
            code=INDIRECT_FIXTURE_ALLOC,
            label=INDIRECT_LABELS[INDIRECT_FIXTURE_ALLOC],
            amount=quantize_money(alloc.fixture_alloc_fee),
            sort_no=8,
        )
    )
    return lines
