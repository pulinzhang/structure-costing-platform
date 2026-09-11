"""总成月核价 — 纯函数 rollup 引擎（无 IO）。

规则见 docs/costing/assembly-costing-design.md。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.common.money import Q4

FORMULA_VERSION = "assembly-v1"

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
    calc_status: str | None = None


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
    node_level: int
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
    should_cost: Decimal = Decimal("0")
    vendor_quote: Decimal | None = None
    gap_amount: Decimal | None = None
    vendor_name: str | None = None
    source_node_id: int | None = None
    level: int = 0
    is_tree_root: bool = False
    parent_node_id: int | None = None
    root_part_number: str | None = None
    root_part_name: str | None = None
    identities_ok: bool = True
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
    conflicted_part_numbers: frozenset[str] | None = None,
) -> tuple[Literal["stamping", "annual"] | None, Decimal | None, str | None]:
    """返回 (source, unit, match_hint)。"""
    conflicted = conflicted_part_numbers or frozenset()
    if part_number in conflicted:
        return None, None, "multi_supplier_unit_cost"
    if part_number in stamping_prices:
        return "stamping", stamping_prices[part_number], None
    if part_number in annual_prices:
        return "annual", annual_prices[part_number], None
    base = base_part_number_before_dash(part_number)
    if base is not None and base in conflicted:
        return None, None, "multi_supplier_unit_cost"
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


def _node_qty(node: RollupBomNode) -> Decimal:
    return node.qty if node.qty is not None else Decimal("1")


def _sorted_children(
    children_by_parent: dict[int | None, list[RollupBomNode]],
    node_id: int,
) -> list[RollupBomNode]:
    kids = children_by_parent.get(node_id, [])
    return sorted(kids, key=lambda n: (n.sort_no, n.id))


def _collect_descendants(
    children_by_parent: dict[int | None, list[RollupBomNode]],
    node_id: int,
) -> list[RollupBomNode]:
    found: list[RollupBomNode] = []
    stack = list(_sorted_children(children_by_parent, node_id))
    while stack:
        current = stack.pop(0)
        found.append(current)
        stack.extend(_sorted_children(children_by_parent, current.id))
    return found


def _path_qty_from_root_child(
    children_by_parent: dict[int | None, list[RollupBomNode]],
    by_id: dict[int, RollupBomNode],
    root_id: int,
    target_id: int,
) -> Decimal:
    """从核价根的直接子走到 target 的 qty 连乘（不含根 qty）。"""
    chain: list[RollupBomNode] = []
    current_id: int | None = target_id
    while current_id is not None and current_id != root_id:
        node = by_id.get(current_id)
        if node is None:
            break
        chain.append(node)
        current_id = node.parent_id
    product = Decimal("1")
    for node in reversed(chain):
        product *= _node_qty(node)
    return product


def identities_hold(
    *,
    stamping_amount: Decimal,
    purchased_amount: Decimal,
    bundle_amount: Decimal,
    material_amount: Decimal,
    welding_amount: Decimal,
    welding_other_fee: Decimal,
    total_amount: Decimal,
    should_cost: Decimal,
    gauge_alloc_fee: Decimal,
    fixture_alloc_fee: Decimal,
    allocation_fee_total: Decimal,
    indirect_amount: Decimal,
    grand_total: Decimal,
    indirect_sum: Decimal,
) -> bool:
    checks = (
        material_amount == quantize_money(stamping_amount + purchased_amount + bundle_amount),
        total_amount == quantize_money(material_amount + welding_amount + welding_other_fee),
        should_cost == total_amount,
        allocation_fee_total == quantize_money(gauge_alloc_fee + fixture_alloc_fee),
        indirect_amount == quantize_money(indirect_sum),
        grand_total == quantize_money(total_amount + indirect_amount),
    )
    return all(checks)


def rollup_assembly(
    root: RollupBomNode,
    children_by_parent: dict[int | None, list[RollupBomNode]],
    stamping_prices: dict[str, Decimal],
    annual_prices: dict[str, Decimal],
    welding: RollupWeldingFee | None,
    packaging: RollupPackagingFee | None = None,
    rates: RollupFinishedRates | None = None,
    allocation: RollupAllocationFees | None = None,
    annual_suppliers: dict[str, str] | None = None,
    conflicted_part_numbers: frozenset[str] | None = None,
    nodes_by_id: dict[int, RollupBomNode] | None = None,
) -> RollupResult:
    """单个核价卡：材料 walk + 本卡焊接 + 间接。公式与 level 无关。"""
    stamp = Decimal("0")
    purchased = Decimal("0")
    bundle = Decimal("0")
    lines: list[RollupLine] = []
    missing_count = 0
    sort_counter = 0
    finished_rates = rates or RollupFinishedRates()
    conflicted = conflicted_part_numbers or frozenset()
    by_id = nodes_by_id or {}
    if not by_id:
        for kids in children_by_parent.values():
            for node in kids:
                by_id[node.id] = node
        by_id[root.id] = root

    def next_sort() -> int:
        nonlocal sort_counter
        sort_counter += 1
        return sort_counter

    def emit_leaf(node: RollupBomNode, path_qty: Decimal) -> None:
        nonlocal stamp, purchased, missing_count
        source, unit, hint = lookup_leaf_price(
            node.part_number,
            stamping_prices,
            annual_prices,
            conflicted,
        )
        if source is None or unit is None:
            missing_count += 1
            lines.append(
                RollupLine(
                    node_level=node.level,
                    bom_node_id=node.id,
                    part_number=node.part_number,
                    part_name=node.part_name,
                    node_role=node.node_role,
                    supply_type=_supply_type_of(node),
                    cost_source="missing",
                    unit_price=Decimal("0"),
                    effective_qty=path_qty,
                    line_amount=Decimal("0"),
                    match_hint=hint,
                    sort_no=next_sort(),
                )
            )
            return
        line_amount = quantize_money(unit * path_qty)
        if source == "stamping":
            stamp += line_amount
        else:
            purchased += line_amount
        lines.append(
            RollupLine(
                node_level=node.level,
                bom_node_id=node.id,
                part_number=node.part_number,
                part_name=node.part_name,
                node_role=node.node_role,
                supply_type=_supply_type_of(node),
                cost_source=source,
                unit_price=unit,
                effective_qty=path_qty,
                line_amount=line_amount,
                match_hint=hint,
                sort_no=next_sort(),
            )
        )

    def emit_skipped(node: RollupBomNode, path_qty: Decimal, bundle_part: str) -> None:
        lines.append(
            RollupLine(
                node_level=node.level,
                bom_node_id=node.id,
                part_number=node.part_number,
                part_name=node.part_name,
                node_role=node.node_role,
                supply_type=_supply_type_of(node),
                cost_source="skipped_by_bundle",
                unit_price=Decimal("0"),
                effective_qty=path_qty,
                line_amount=Decimal("0"),
                match_hint=f"bundle_parent:{bundle_part}",
                sort_no=next_sort(),
            )
        )

    def walk(node: RollupBomNode, path_qty: Decimal) -> None:
        nonlocal bundle
        kids = _sorted_children(children_by_parent, node.id)
        if not kids:
            emit_leaf(node, path_qty)
            return
        for child in kids:
            child_qty = path_qty * _node_qty(child)
            grandchildren = _sorted_children(children_by_parent, child.id)
            if grandchildren and child.part_number in annual_prices:
                bundle_unit = annual_prices[child.part_number]
                line_amount = quantize_money(bundle_unit * child_qty)
                bundle += line_amount
                lines.append(
                    RollupLine(
                        node_level=child.level,
                        bom_node_id=child.id,
                        part_number=child.part_number,
                        part_name=child.part_name,
                        node_role=child.node_role,
                        supply_type=_supply_type_of(child),
                        cost_source="bundle",
                        unit_price=bundle_unit,
                        effective_qty=child_qty,
                        line_amount=line_amount,
                        sort_no=next_sort(),
                    )
                )
                for descendant in _collect_descendants(children_by_parent, child.id):
                    desc_qty = _path_qty_from_root_child(
                        children_by_parent, by_id, root.id, descendant.id
                    )
                    emit_skipped(descendant, desc_qty, child.part_number)
            elif grandchildren:
                walk(child, child_qty)
            else:
                emit_leaf(child, child_qty)

    walk(root, Decimal("1"))

    if welding is None:
        weld_amount = Decimal("0")
        weld_other = Decimal("0")
        weld_incomplete = False
        welding_fee_id = None
        welding_summary = None
    else:
        weld_amount = welding.final_amount
        weld_other = welding.other_fee
        weld_incomplete = welding.missing_price_count > 0 or (
            welding.calc_status is not None and welding.calc_status != "ok"
        )
        welding_fee_id = welding.welding_fee_id
        welding_summary = welding.summary

    material = quantize_money(stamp + purchased + bundle)
    weld_q = quantize_money(weld_amount)
    weld_other_q = quantize_money(weld_other)
    total = quantize_money(material + weld_q + weld_other_q)
    should_cost = total

    vendor_quote: Decimal | None = None
    vendor_name: str | None = None
    gap_amount: Decimal | None = None
    if root.part_number in annual_prices:
        vendor_quote = quantize_money(annual_prices[root.part_number])
        if annual_suppliers:
            vendor_name = annual_suppliers.get(root.part_number)
        gap_amount = quantize_money(vendor_quote - should_cost)

    indirect_lines = build_indirect_lines(
        monthly_total=total,
        packaging=packaging,
        rates=finished_rates,
        allocation=allocation,
    )
    by_code = {item.code: item.amount for item in indirect_lines}
    indirect_sum = sum((item.amount for item in indirect_lines), Decimal("0"))
    indirect = quantize_money(indirect_sum)
    alloc_total = quantize_money(
        by_code.get(INDIRECT_GAUGE_ALLOC, Decimal("0"))
        + by_code.get(INDIRECT_FIXTURE_ALLOC, Decimal("0"))
    )
    grand = quantize_money(total + indirect)
    ok_ids = identities_hold(
        stamping_amount=quantize_money(stamp),
        purchased_amount=quantize_money(purchased),
        bundle_amount=quantize_money(bundle),
        material_amount=material,
        welding_amount=weld_q,
        welding_other_fee=weld_other_q,
        total_amount=total,
        should_cost=should_cost,
        gauge_alloc_fee=by_code.get(INDIRECT_GAUGE_ALLOC, Decimal("0")),
        fixture_alloc_fee=by_code.get(INDIRECT_FIXTURE_ALLOC, Decimal("0")),
        allocation_fee_total=alloc_total,
        indirect_amount=indirect,
        grand_total=grand,
        indirect_sum=indirect_sum,
    )
    if missing_count == 0 and not weld_incomplete:
        status: CalcStatus = "ok"
    else:
        status = "partial"

    tree_root = root.parent_id is None
    ancestor = root
    while ancestor.parent_id is not None and ancestor.parent_id in by_id:
        ancestor = by_id[ancestor.parent_id]

    return RollupResult(
        part_number=root.part_number,
        part_name=root.part_name,
        supply_qty=_node_qty(root),
        sketch_url=root.sketch_url,
        status=status,
        stamping_amount=quantize_money(stamp),
        purchased_amount=quantize_money(purchased),
        bundle_amount=quantize_money(bundle),
        material_amount=material,
        welding_amount=weld_q,
        welding_other_fee=weld_other_q,
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
        should_cost=should_cost,
        vendor_quote=vendor_quote,
        gap_amount=gap_amount,
        vendor_name=vendor_name,
        source_node_id=root.id,
        level=root.level,
        is_tree_root=tree_root,
        parent_node_id=root.parent_id,
        root_part_number=ancestor.part_number,
        root_part_name=ancestor.part_name,
        identities_ok=ok_ids,
        lines=lines,
        indirect_lines=indirect_lines,
    )
