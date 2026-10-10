"""总成月核价 — 纯函数 rollup 引擎（无 IO）。

规则见 docs/costing/assembly-costing-design.md。
恒等式 / 间接费 / 树遍历拆在同目录；本文件只走材料 + 焊接 + 间接。
"""

from __future__ import annotations

from decimal import Decimal

from app.services.costing.assembly_cost.calc.identities import identities_hold, quantize_money
from app.services.costing.assembly_cost.calc.indirects import build_indirect_lines
from app.services.costing.assembly_cost.calc.rollup_models import (
    FORMULA_VERSION,
    INDIRECT_FINANCE,
    INDIRECT_FIXTURE_ALLOC,
    INDIRECT_GAUGE_ALLOC,
    INDIRECT_MANAGEMENT,
    INDIRECT_PRETAX_PROFIT,
    INDIRECT_SCRAP,
    INDIRECT_UNIT_TRANSPORT,
    INDIRECT_WAREHOUSE_BUNDLING,
    CalcStatus,
    CostSource,
    RollupAllocationFees,
    RollupBomNode,
    RollupFinishedRates,
    RollupIndirectLine,
    RollupLine,
    RollupPackagingFee,
    RollupResult,
    RollupWeldingFee,
)
from app.services.costing.assembly_cost.calc.tree import (
    base_part_number_before_dash,
    collect_descendants,
    index_nodes,
    lookup_leaf_price,
    node_qty,
    path_qty_from_root_child,
    sorted_children,
    supply_type_of,
)
from app.services.costing.assembly_cost.codes import is_purchased_assembly_root

__all__ = [
    "FORMULA_VERSION",
    "CalcStatus",
    "CostSource",
    "INDIRECT_FIXTURE_ALLOC",
    "INDIRECT_FINANCE",
    "INDIRECT_GAUGE_ALLOC",
    "INDIRECT_MANAGEMENT",
    "INDIRECT_PRETAX_PROFIT",
    "INDIRECT_SCRAP",
    "INDIRECT_UNIT_TRANSPORT",
    "INDIRECT_WAREHOUSE_BUNDLING",
    "RollupAllocationFees",
    "RollupBomNode",
    "RollupFinishedRates",
    "RollupIndirectLine",
    "RollupLine",
    "RollupPackagingFee",
    "RollupResult",
    "RollupWeldingFee",
    "base_part_number_before_dash",
    "build_indirect_lines",
    "identities_hold",
    "lookup_leaf_price",
    "quantize_money",
    "rollup_assembly",
]


def rollup_assembly(
    root: RollupBomNode,
    children_by_parent: dict[int | None, list[RollupBomNode]],
    stamping_prices: dict[str, Decimal],
    annual_prices: dict[str, Decimal],
    welding: RollupWeldingFee | None,
    rates: RollupFinishedRates,
    packaging: RollupPackagingFee | None = None,
    allocation: RollupAllocationFees | None = None,
    annual_suppliers: dict[str, str] | None = None,
    conflicted_part_numbers: frozenset[str] | None = None,
    nodes_by_id: dict[int, RollupBomNode] | None = None,
) -> RollupResult:
    """单个核价卡：材料 walk + 本卡焊接 + 间接。公式与 level 无关。

    外购件总成（本卡根有子件且命中年度价）：材料用年度价，子孙已含不报缺价，
    焊接也不再抄——年度价已是结算价。自制分总成仍拆子件并抄本卡焊费。
    """
    stamp = Decimal("0")
    purchased = Decimal("0")
    bundle = Decimal("0")
    lines: list[RollupLine] = []
    missing_count = 0
    sort_counter = 0
    conflicted = conflicted_part_numbers or frozenset()
    by_id = index_nodes(root, children_by_parent, nodes_by_id)

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
                    supply_type=supply_type_of(node),
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
                supply_type=supply_type_of(node),
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
                supply_type=supply_type_of(node),
                cost_source="skipped_by_bundle",
                unit_price=Decimal("0"),
                effective_qty=path_qty,
                line_amount=Decimal("0"),
                match_hint=f"bundle_parent:{bundle_part}",
                sort_no=next_sort(),
            )
        )

    def emit_bundle(node: RollupBomNode, path_qty: Decimal) -> None:
        nonlocal bundle
        bundle_unit = annual_prices[node.part_number]
        line_amount = quantize_money(bundle_unit * path_qty)
        bundle += line_amount
        lines.append(
            RollupLine(
                node_level=node.level,
                bom_node_id=node.id,
                part_number=node.part_number,
                part_name=node.part_name,
                node_role=node.node_role,
                supply_type=supply_type_of(node),
                cost_source="bundle",
                unit_price=bundle_unit,
                effective_qty=path_qty,
                line_amount=line_amount,
                sort_no=next_sort(),
            )
        )
        for descendant in collect_descendants(children_by_parent, node.id):
            desc_qty = path_qty_from_root_child(by_id, root.id, descendant.id)
            emit_skipped(descendant, desc_qty, node.part_number)

    def walk(node: RollupBomNode, path_qty: Decimal) -> None:
        kids = sorted_children(children_by_parent, node.id)
        if not kids:
            emit_leaf(node, path_qty)
            return
        if node.part_number in annual_prices:
            emit_bundle(node, path_qty)
            return
        for child in kids:
            walk(child, path_qty * node_qty(child))

    walk(root, Decimal("1"))

    # P4：外购件总成年度价已含工费，本卡不抄焊接、不因上游焊费 partial 报缺价。
    is_purchased_root = is_purchased_assembly_root(root.id, lines)
    if is_purchased_root or welding is None:
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
        rates=rates,
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
    status: CalcStatus = "ok" if missing_count == 0 and not weld_incomplete else "partial"

    tree_root = root.parent_id is None
    ancestor = root
    while ancestor.parent_id is not None and ancestor.parent_id in by_id:
        ancestor = by_id[ancestor.parent_id]

    return RollupResult(
        part_number=root.part_number,
        part_name=root.part_name,
        supply_qty=node_qty(root),
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
        finance_rate=rates.finance_rate,
        management_rate=rates.management_rate,
        scrap_rate=rates.scrap_rate,
        pretax_profit_rate=rates.pretax_profit_rate,
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
