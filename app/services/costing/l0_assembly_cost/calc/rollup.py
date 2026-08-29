"""成品月核价 — 纯函数 rollup 引擎（无 IO）。

规则见 docs/costing/l0-assembly-costing-design.md。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from app.common.money import Q4

FORMULA_VERSION = "l0-assembly-v1"

CostSource = Literal["stamping", "annual", "bundle", "skipped_by_bundle", "missing"]
CalcStatus = Literal["ok", "partial"]

INDIRECT_UNIT_TRANSPORT = "unit_transport_fee"
INDIRECT_WAREHOUSE_BUNDLING = "warehouse_bundling_fee"
INDIRECT_FINANCE = "finished_finance_fee"
INDIRECT_MANAGEMENT = "finished_management_fee"
INDIRECT_SCRAP = "finished_scrap_fee"
INDIRECT_PRETAX_PROFIT = "finished_pretax_profit_fee"
INDIRECT_GAUGE_ALLOC = "gauge_alloc_fee"
INDIRECT_FIXTURE_ALLOC = "fixture_alloc_fee"

_INDIRECT_LABELS: dict[str, str] = {
    INDIRECT_UNIT_TRANSPORT: "单件运输费",
    INDIRECT_WAREHOUSE_BUNDLING: "仓储费+捆包费",
    INDIRECT_FINANCE: "财务费",
    INDIRECT_MANAGEMENT: "管理费",
    INDIRECT_SCRAP: "报废费用",
    INDIRECT_PRETAX_PROFIT: "税前利润",
    INDIRECT_GAUGE_ALLOC: "检具分摊费",
    INDIRECT_FIXTURE_ALLOC: "器具分摊费",
}


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Q4, rounding=ROUND_HALF_UP)


def _format_rate_label(base_label: str, rate: Decimal) -> str:
    if rate == 0:
        return base_label
    permille = rate * Decimal("1000")
    if permille == permille.to_integral_value() and rate < Decimal("0.01"):
        return f"{base_label}（{permille.to_integral_value()}‰）"
    percent = rate * Decimal("100")
    if percent == percent.to_integral_value():
        return f"{base_label}（{percent.to_integral_value()}%）"
    return f"{base_label}（{percent.normalize()}%）"


@dataclass(frozen=True)
class RollupBomNode:
    id: int
    parent_id: int | None
    level: int
    part_number: str
    part_name: str | None
    qty: Decimal
    node_role: str
    sort_no: int = 0
    supply_type: str | None = None
    sketch_url: str | None = None


@dataclass(frozen=True)
class RollupWeldingFee:
    final_amount: Decimal
    other_fee: Decimal = Decimal("0")
    missing_price_count: int = 0
    welding_fee_id: int | None = None
    summary: str | None = None


@dataclass(frozen=True)
class RollupPackagingFee:
    unit_transport_fee: Decimal = Decimal("0")
    warehouse_bundling_fee: Decimal = Decimal("0")


@dataclass(frozen=True)
class RollupFinishedRates:
    finance_rate: Decimal = Decimal("0.02")
    management_rate: Decimal = Decimal("0.02")
    scrap_rate: Decimal = Decimal("0.003")
    pretax_profit_rate: Decimal = Decimal("0.02")


@dataclass(frozen=True)
class RollupAllocationFees:
    """检具/器具分摊（上游未建时为 0，仍计入 grand_total）。"""

    gauge_alloc_fee: Decimal = Decimal("0")
    fixture_alloc_fee: Decimal = Decimal("0")


@dataclass(frozen=True)
class RollupLine:
    level_label: str
    bom_node_id: int | None
    part_number: str
    part_name: str | None
    node_role: str | None
    supply_type: str | None
    cost_source: CostSource
    unit_price: Decimal
    effective_qty: Decimal
    line_amount: Decimal
    match_hint: str | None = None
    sort_no: int = 0


@dataclass(frozen=True)
class RollupIndirectLine:
    code: str
    label: str
    amount: Decimal
    rate: Decimal | None = None
    base_amount: Decimal | None = None
    sort_no: int = 0


@dataclass
class RollupResult:
    part_number: str
    part_name: str | None
    supply_qty: Decimal
    sketch_url: str | None
    status: CalcStatus
    stamping_amount: Decimal
    purchased_amount: Decimal
    bundle_amount: Decimal
    material_amount: Decimal
    welding_amount: Decimal
    welding_other_fee: Decimal
    total_amount: Decimal
    unit_transport_fee: Decimal
    warehouse_bundling_fee: Decimal
    finished_finance_fee: Decimal
    finished_management_fee: Decimal
    finished_scrap_fee: Decimal
    finished_pretax_profit_fee: Decimal
    gauge_alloc_fee: Decimal
    fixture_alloc_fee: Decimal
    allocation_fee_total: Decimal
    indirect_amount: Decimal
    grand_total: Decimal
    finance_rate: Decimal
    management_rate: Decimal
    scrap_rate: Decimal
    pretax_profit_rate: Decimal
    welding_fee_id: int | None
    welding_summary: str | None
    missing_leaf_count: int
    lines: list[RollupLine] = field(default_factory=list)
    indirect_lines: list[RollupIndirectLine] = field(default_factory=list)
    formula_version: str = FORMULA_VERSION


def base_part_number_before_dash(part_number: str) -> str | None:
    if "-" not in part_number:
        return None
    base = part_number.split("-", 1)[0].strip()
    return base or None


def lookup_leaf_price(
    part_number: str,
    stamping_prices: dict[str, Decimal],
    annual_prices: dict[str, Decimal],
) -> tuple[Literal["stamping", "annual"] | None, Decimal | None, str | None]:
    """返回 (source, unit, match_hint)。"""
    if part_number in stamping_prices:
        return "stamping", stamping_prices[part_number], None
    if part_number in annual_prices:
        return "annual", annual_prices[part_number], None
    base = base_part_number_before_dash(part_number)
    if base is not None and base in stamping_prices:
        return "stamping", stamping_prices[base], f"dash_fallback:{base}"
    return None, None, None


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
            label=_INDIRECT_LABELS[INDIRECT_UNIT_TRANSPORT],
            amount=quantize_money(transport),
            sort_no=1,
        ),
        RollupIndirectLine(
            code=INDIRECT_WAREHOUSE_BUNDLING,
            label=_INDIRECT_LABELS[INDIRECT_WAREHOUSE_BUNDLING],
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
                label=_format_rate_label(_INDIRECT_LABELS[code], rate),
                amount=quantize_money(monthly_total * rate),
                rate=rate,
                base_amount=monthly_total,
                sort_no=sort_no,
            )
        )
    lines.append(
        RollupIndirectLine(
            code=INDIRECT_GAUGE_ALLOC,
            label=_INDIRECT_LABELS[INDIRECT_GAUGE_ALLOC],
            amount=quantize_money(alloc.gauge_alloc_fee),
            sort_no=7,
        )
    )
    lines.append(
        RollupIndirectLine(
            code=INDIRECT_FIXTURE_ALLOC,
            label=_INDIRECT_LABELS[INDIRECT_FIXTURE_ALLOC],
            amount=quantize_money(alloc.fixture_alloc_fee),
            sort_no=8,
        )
    )
    return lines


def _supply_type_of(node: RollupBomNode) -> str | None:
    return node.supply_type or node.node_role


def rollup_l0(
    l0: RollupBomNode,
    children_by_parent: dict[int | None, list[RollupBomNode]],
    stamping_prices: dict[str, Decimal],
    annual_prices: dict[str, Decimal],
    welding: RollupWeldingFee | None,
    packaging: RollupPackagingFee | None = None,
    rates: RollupFinishedRates | None = None,
    allocation: RollupAllocationFees | None = None,
) -> RollupResult:
    """单个 L0：材料 rollup + 焊接 + 间接 → 总费用。"""
    stamp = Decimal("0")
    purchased = Decimal("0")
    bundle = Decimal("0")
    lines: list[RollupLine] = []
    missing_count = 0
    sort_counter = 0
    finished_rates = rates or RollupFinishedRates()

    def next_sort() -> int:
        nonlocal sort_counter
        sort_counter += 1
        return sort_counter

    l1_nodes = sorted(children_by_parent.get(l0.id, []), key=lambda n: n.sort_no)

    for l1 in l1_nodes:
        l1_qty = l1.qty if l1.qty is not None else Decimal("1")
        l2_nodes = sorted(children_by_parent.get(l1.id, []), key=lambda n: n.sort_no)

        if l2_nodes:
            if l1.part_number in annual_prices:
                bundle_unit = annual_prices[l1.part_number]
                line_amount = quantize_money(bundle_unit * l1_qty)
                bundle += line_amount
                lines.append(
                    RollupLine(
                        level_label="L1-bundle",
                        bom_node_id=l1.id,
                        part_number=l1.part_number,
                        part_name=l1.part_name,
                        node_role=l1.node_role,
                        supply_type=_supply_type_of(l1),
                        cost_source="bundle",
                        unit_price=bundle_unit,
                        effective_qty=l1_qty,
                        line_amount=line_amount,
                        sort_no=next_sort(),
                    )
                )
                for l2 in l2_nodes:
                    l2_qty = l2.qty if l2.qty is not None else Decimal("1")
                    effective_qty = l1_qty * l2_qty
                    lines.append(
                        RollupLine(
                            level_label="L2",
                            bom_node_id=l2.id,
                            part_number=l2.part_number,
                            part_name=l2.part_name,
                            node_role=l2.node_role,
                            supply_type=_supply_type_of(l2),
                            cost_source="skipped_by_bundle",
                            unit_price=Decimal("0"),
                            effective_qty=effective_qty,
                            line_amount=Decimal("0"),
                            match_hint=f"bundle_parent:{l1.part_number}",
                            sort_no=next_sort(),
                        )
                    )
                continue

            for l2 in l2_nodes:
                l2_qty = l2.qty if l2.qty is not None else Decimal("1")
                effective_qty = l1_qty * l2_qty
                source, unit, hint = lookup_leaf_price(
                    l2.part_number, stamping_prices, annual_prices
                )
                if source is None or unit is None:
                    missing_count += 1
                    lines.append(
                        RollupLine(
                            level_label="L2",
                            bom_node_id=l2.id,
                            part_number=l2.part_number,
                            part_name=l2.part_name,
                            node_role=l2.node_role,
                            supply_type=_supply_type_of(l2),
                            cost_source="missing",
                            unit_price=Decimal("0"),
                            effective_qty=effective_qty,
                            line_amount=Decimal("0"),
                            sort_no=next_sort(),
                        )
                    )
                    continue
                line_amount = quantize_money(unit * effective_qty)
                if source == "stamping":
                    stamp += line_amount
                else:
                    purchased += line_amount
                lines.append(
                    RollupLine(
                        level_label="L2",
                        bom_node_id=l2.id,
                        part_number=l2.part_number,
                        part_name=l2.part_name,
                        node_role=l2.node_role,
                        supply_type=_supply_type_of(l2),
                        cost_source=source,
                        unit_price=unit,
                        effective_qty=effective_qty,
                        line_amount=line_amount,
                        match_hint=hint,
                        sort_no=next_sort(),
                    )
                )
            continue

        source, unit, hint = lookup_leaf_price(l1.part_number, stamping_prices, annual_prices)
        if source is None or unit is None:
            missing_count += 1
            lines.append(
                RollupLine(
                    level_label="L1-leaf",
                    bom_node_id=l1.id,
                    part_number=l1.part_number,
                    part_name=l1.part_name,
                    node_role=l1.node_role,
                    supply_type=_supply_type_of(l1),
                    cost_source="missing",
                    unit_price=Decimal("0"),
                    effective_qty=l1_qty,
                    line_amount=Decimal("0"),
                    sort_no=next_sort(),
                )
            )
            continue
        line_amount = quantize_money(unit * l1_qty)
        if source == "stamping":
            stamp += line_amount
        else:
            purchased += line_amount
        lines.append(
            RollupLine(
                level_label="L1-leaf",
                bom_node_id=l1.id,
                part_number=l1.part_number,
                part_name=l1.part_name,
                node_role=l1.node_role,
                supply_type=_supply_type_of(l1),
                cost_source=source,
                unit_price=unit,
                effective_qty=l1_qty,
                line_amount=line_amount,
                match_hint=hint,
                sort_no=next_sort(),
            )
        )

    if welding is None:
        weld_amount = Decimal("0")
        weld_other = Decimal("0")
        weld_incomplete = True
        welding_fee_id = None
        welding_summary = None
    else:
        weld_amount = welding.final_amount
        weld_other = welding.other_fee
        weld_incomplete = welding.missing_price_count > 0
        welding_fee_id = welding.welding_fee_id
        welding_summary = welding.summary

    material = quantize_money(stamp + purchased + bundle)
    total = quantize_money(material + weld_amount + weld_other)

    indirect_lines = build_indirect_lines(
        monthly_total=total,
        packaging=packaging,
        rates=finished_rates,
        allocation=allocation,
    )
    by_code = {item.code: item.amount for item in indirect_lines}
    indirect = quantize_money(sum((item.amount for item in indirect_lines), Decimal("0")))
    alloc_total = quantize_money(
        by_code.get(INDIRECT_GAUGE_ALLOC, Decimal("0"))
        + by_code.get(INDIRECT_FIXTURE_ALLOC, Decimal("0"))
    )
    grand = quantize_money(total + indirect)
    status: CalcStatus = "ok" if (missing_count == 0 and not weld_incomplete) else "partial"

    return RollupResult(
        part_number=l0.part_number,
        part_name=l0.part_name,
        supply_qty=l0.qty if l0.qty is not None else Decimal("1"),
        sketch_url=l0.sketch_url,
        status=status,
        stamping_amount=quantize_money(stamp),
        purchased_amount=quantize_money(purchased),
        bundle_amount=quantize_money(bundle),
        material_amount=material,
        welding_amount=quantize_money(weld_amount),
        welding_other_fee=quantize_money(weld_other),
        total_amount=total,
        unit_transport_fee=by_code.get(INDIRECT_UNIT_TRANSPORT, Decimal("0")),
        warehouse_bundling_fee=by_code.get(INDIRECT_WAREHOUSE_BUNDLING, Decimal("0")),
        finished_finance_fee=by_code.get(INDIRECT_FINANCE, Decimal("0")),
        finished_management_fee=by_code.get(INDIRECT_MANAGEMENT, Decimal("0")),
        finished_scrap_fee=by_code.get(INDIRECT_SCRAP, Decimal("0")),
        finished_pretax_profit_fee=by_code.get(INDIRECT_PRETAX_PROFIT, Decimal("0")),
        gauge_alloc_fee=by_code.get(INDIRECT_GAUGE_ALLOC, Decimal("0")),
        fixture_alloc_fee=by_code.get(INDIRECT_FIXTURE_ALLOC, Decimal("0")),
        allocation_fee_total=alloc_total,
        indirect_amount=indirect,
        grand_total=grand,
        finance_rate=finished_rates.finance_rate,
        management_rate=finished_rates.management_rate,
        scrap_rate=finished_rates.scrap_rate,
        pretax_profit_rate=finished_rates.pretax_profit_rate,
        welding_fee_id=welding_fee_id,
        welding_summary=welding_summary,
        missing_leaf_count=missing_count,
        lines=lines,
        indirect_lines=indirect_lines,
    )
