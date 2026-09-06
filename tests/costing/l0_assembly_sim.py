"""
成品（L0）月核价 — 测试适配层

计算真相在 app.services.costing.assembly_cost.calc.rollup；
本模块仅做入参/出参适配与报告格式化，避免双轨公式。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from app.services.costing.assembly_cost.calc.rollup import (
    INDIRECT_FINANCE,
    INDIRECT_FIXTURE_ALLOC,
    INDIRECT_GAUGE_ALLOC,
    INDIRECT_MANAGEMENT,
    INDIRECT_PRETAX_PROFIT,
    INDIRECT_SCRAP,
    INDIRECT_UNIT_TRANSPORT,
    INDIRECT_WAREHOUSE_BUNDLING,
    RollupBomNode,
    RollupFinishedRates,
    RollupPackagingFee,
    RollupResult,
    RollupWeldingFee,
    quantize_money,
    rollup_l0,
)

# 兼容旧测试常量名
INDIRECT_PACKAGING_OTHER = INDIRECT_WAREHOUSE_BUNDLING

__all__ = [
    "INDIRECT_FINANCE",
    "INDIRECT_FIXTURE_ALLOC",
    "INDIRECT_GAUGE_ALLOC",
    "INDIRECT_MANAGEMENT",
    "INDIRECT_PACKAGING_OTHER",
    "INDIRECT_PRETAX_PROFIT",
    "INDIRECT_SCRAP",
    "INDIRECT_UNIT_TRANSPORT",
    "INDIRECT_WAREHOUSE_BUNDLING",
    "L0SimResult",
    "SimBomNode",
    "SimFinishedRates",
    "SimIndirectLine",
    "SimLine",
    "SimMissing",
    "SimPackagingTransportFee",
    "SimWeldingFee",
    "format_l0_cost_breakdown",
    "format_simulation_report",
    "quantize_money",
    "simulate_all_l0",
    "simulate_l0",
]


@dataclass(frozen=True)
class SimBomNode:
    id: int
    parent_id: int | None
    level: int
    part_number: str
    part_name: str | None
    qty: Decimal
    node_role: str
    sort_no: int = 0


@dataclass(frozen=True)
class SimWeldingFee:
    final_amount: Decimal
    other_fee: Decimal = Decimal("0")
    missing_price_count: int = 0


@dataclass(frozen=True)
class SimPackagingTransportFee:
    """源字段 other_fee → 结果 warehouse_bundling_fee。"""

    unit_transport_fee: Decimal = Decimal("0")
    other_fee: Decimal = Decimal("0")


@dataclass(frozen=True)
class SimFinishedRates:
    finance_rate: Decimal = Decimal("0.02")
    management_rate: Decimal = Decimal("0.02")
    scrap_rate: Decimal = Decimal("0.003")
    pretax_profit_rate: Decimal = Decimal("0.02")


@dataclass(frozen=True)
class SimLine:
    level_label: str
    part_number: str
    source: Literal["stamping", "annual", "bundle", "skipped_by_bundle", "missing"]
    unit_price: Decimal
    effective_qty: Decimal
    line_amount: Decimal


@dataclass(frozen=True)
class SimMissing:
    part_number: str
    part_name: str | None
    node_role: str
    effective_qty: Decimal


@dataclass(frozen=True)
class SimIndirectLine:
    code: str
    label: str
    amount: Decimal
    rate: Decimal | None = None
    base_amount: Decimal | None = None


@dataclass
class L0SimResult:
    part_number: str
    part_name: str | None
    status: Literal["ok", "partial"]
    stamping_amount: Decimal
    purchased_amount: Decimal
    bundle_amount: Decimal
    welding_amount: Decimal
    other_fee: Decimal
    total_amount: Decimal
    indirect_lines: list[SimIndirectLine] = field(default_factory=list)
    indirect_amount: Decimal = Decimal("0")
    grand_total: Decimal = Decimal("0")
    missing: list[SimMissing] = field(default_factory=list)
    lines: list[SimLine] = field(default_factory=list)

    def indirect_amount_of(self, code: str) -> Decimal:
        for item in self.indirect_lines:
            if item.code == code:
                return item.amount
        return Decimal("0.0000")

    @property
    def unit_transport_fee(self) -> Decimal:
        return self.indirect_amount_of(INDIRECT_UNIT_TRANSPORT)

    @property
    def warehouse_bundling_fee(self) -> Decimal:
        return self.indirect_amount_of(INDIRECT_WAREHOUSE_BUNDLING)

    @property
    def packaging_other_fee(self) -> Decimal:
        """兼容旧断言名 → warehouse_bundling_fee。"""
        return self.warehouse_bundling_fee

    @property
    def finished_finance_fee(self) -> Decimal:
        return self.indirect_amount_of(INDIRECT_FINANCE)

    @property
    def finished_management_fee(self) -> Decimal:
        return self.indirect_amount_of(INDIRECT_MANAGEMENT)

    @property
    def finished_scrap_fee(self) -> Decimal:
        return self.indirect_amount_of(INDIRECT_SCRAP)

    @property
    def finished_pretax_profit_fee(self) -> Decimal:
        return self.indirect_amount_of(INDIRECT_PRETAX_PROFIT)


def _to_rollup_node(node: SimBomNode) -> RollupBomNode:
    return RollupBomNode(
        id=node.id,
        parent_id=node.parent_id,
        level=node.level,
        part_number=node.part_number,
        part_name=node.part_name,
        qty=node.qty,
        node_role=node.node_role,
        sort_no=node.sort_no,
    )


def _from_rollup(result: RollupResult) -> L0SimResult:
    missing: list[SimMissing] = []
    lines: list[SimLine] = []
    for line in result.lines:
        if line.cost_source == "missing":
            missing.append(
                SimMissing(
                    part_number=line.part_number,
                    part_name=line.part_name,
                    node_role=line.node_role or "",
                    effective_qty=line.effective_qty,
                )
            )
        lines.append(
            SimLine(
                level_label=f"L{line.node_level}",
                part_number=line.part_number,
                source=line.cost_source,
                unit_price=line.unit_price,
                effective_qty=line.effective_qty,
                line_amount=line.line_amount,
            )
        )
    return L0SimResult(
        part_number=result.part_number,
        part_name=result.part_name,
        status=result.status,
        stamping_amount=result.stamping_amount,
        purchased_amount=result.purchased_amount,
        bundle_amount=result.bundle_amount,
        welding_amount=result.welding_amount,
        other_fee=result.welding_other_fee,
        total_amount=result.total_amount,
        indirect_lines=[
            SimIndirectLine(
                code=item.code,
                label=item.label,
                amount=item.amount,
                rate=item.rate,
                base_amount=item.base_amount,
            )
            for item in result.indirect_lines
        ],
        indirect_amount=result.indirect_amount,
        grand_total=result.grand_total,
        missing=missing,
        lines=lines,
    )


def simulate_l0(
    l0: SimBomNode,
    children_by_parent: dict[int | None, list[SimBomNode]],
    stamping_prices: dict[str, Decimal],
    annual_prices: dict[str, Decimal],
    welding: SimWeldingFee | None,
    packaging: SimPackagingTransportFee | None = None,
    rates: SimFinishedRates | None = None,
) -> L0SimResult:
    """委托生产 rollup_l0。"""
    children: dict[int | None, list[RollupBomNode]] = {
        parent_id: [_to_rollup_node(n) for n in kids]
        for parent_id, kids in children_by_parent.items()
    }
    rollup_welding = None
    if welding is not None:
        rollup_welding = RollupWeldingFee(
            final_amount=welding.final_amount,
            other_fee=welding.other_fee,
            missing_price_count=welding.missing_price_count,
        )
    rollup_packaging = None
    if packaging is not None:
        rollup_packaging = RollupPackagingFee(
            unit_transport_fee=packaging.unit_transport_fee,
            warehouse_bundling_fee=packaging.other_fee,
        )
    finished_rates = None
    if rates is not None:
        finished_rates = RollupFinishedRates(
            finance_rate=rates.finance_rate,
            management_rate=rates.management_rate,
            scrap_rate=rates.scrap_rate,
            pretax_profit_rate=rates.pretax_profit_rate,
        )
    return _from_rollup(
        rollup_l0(
            l0=_to_rollup_node(l0),
            children_by_parent=children,
            stamping_prices=stamping_prices,
            annual_prices=annual_prices,
            welding=rollup_welding,
            packaging=rollup_packaging,
            rates=finished_rates,
        )
    )


def simulate_all_l0(
    nodes: list[SimBomNode],
    stamping_prices: dict[str, Decimal],
    annual_prices: dict[str, Decimal],
    welding_by_part: dict[str, SimWeldingFee],
    packaging_by_part: dict[str, SimPackagingTransportFee] | None = None,
    rates: SimFinishedRates | None = None,
) -> list[L0SimResult]:
    children_by_parent: dict[int | None, list[SimBomNode]] = {}
    for node in nodes:
        children_by_parent.setdefault(node.parent_id, []).append(node)

    packaging_map = packaging_by_part or {}
    finished_rates = rates or SimFinishedRates()
    l0_nodes = sorted(
        [n for n in nodes if n.level == 0],
        key=lambda n: (n.sort_no, n.part_number),
    )
    return [
        simulate_l0(
            l0=l0,
            children_by_parent=children_by_parent,
            stamping_prices=stamping_prices,
            annual_prices=annual_prices,
            welding=welding_by_part.get(l0.part_number),
            packaging=packaging_map.get(l0.part_number),
            rates=finished_rates,
        )
        for l0 in l0_nodes
    ]


def format_l0_cost_breakdown(result: L0SimResult) -> str:
    material = quantize_money(
        result.stamping_amount + result.purchased_amount + result.bundle_amount
    )
    out: list[str] = [
        f"{result.part_number}  {result.part_name or ''}  status={result.status}",
        "",
        "【L0 月总账】",
        f"  ① 冲压小计       = {result.stamping_amount}",
        f"  ② 年度价/外购    = {result.purchased_amount}",
        f"  ③ 一口价         = {result.bundle_amount}",
        f"  材料合计         = {material}",
        f"  ④ 焊接费         = {result.welding_amount}",
        f"  ⑤ 焊接其它       = {result.other_fee}",
        "  ────────────────",
        f"  L0 月总账        = {result.total_amount}",
        "",
        "【间接费用 · 一一单列】",
    ]
    for index, item in enumerate(result.indirect_lines, start=1):
        rate_hint = ""
        if item.rate is not None and item.base_amount is not None:
            rate_hint = f"  = {item.base_amount} × {item.rate}"
        out.append(f"  I{index} {item.label:<16} = {item.amount}  ({item.code}){rate_hint}")
    out.extend(
        [
            "  ────────────────",
            f"  间接费用合计     = {result.indirect_amount}",
            "",
            "【总费用】",
            f"  总费用           = {result.total_amount} + {result.indirect_amount}"
            f" = {result.grand_total}",
        ]
    )
    return "\n".join(out)


def format_simulation_report(
    results: list[L0SimResult],
    *,
    title: str,
    stamping_price_count: int,
    annual_price_count: int,
    welding_count: int,
    packaging_count: int = 0,
) -> str:
    ok_n = sum(1 for r in results if r.status == "ok")
    partial_n = sum(1 for r in results if r.status == "partial")
    stamp_sum = quantize_money(sum((r.stamping_amount for r in results), Decimal("0")))
    buy_sum = quantize_money(sum((r.purchased_amount for r in results), Decimal("0")))
    bundle_sum = quantize_money(sum((r.bundle_amount for r in results), Decimal("0")))
    weld_sum = quantize_money(sum((r.welding_amount for r in results), Decimal("0")))
    other_sum = quantize_money(sum((r.other_fee for r in results), Decimal("0")))
    total_all = quantize_money(sum((r.total_amount for r in results), Decimal("0")))
    total_ok = quantize_money(
        sum((r.total_amount for r in results if r.status == "ok"), Decimal("0"))
    )
    indirect_sum = quantize_money(sum((r.indirect_amount for r in results), Decimal("0")))
    grand_all = quantize_money(sum((r.grand_total for r in results), Decimal("0")))
    grand_ok = quantize_money(
        sum((r.grand_total for r in results if r.status == "ok"), Decimal("0"))
    )

    indirect_code_sums: dict[str, Decimal] = {}
    indirect_code_labels: dict[str, str] = {}
    for result in results:
        for item in result.indirect_lines:
            indirect_code_sums[item.code] = quantize_money(
                indirect_code_sums.get(item.code, Decimal("0")) + item.amount
            )
            indirect_code_labels[item.code] = item.label

    miss_count: dict[str, int] = {}
    miss_meta: dict[str, tuple[str | None, str]] = {}
    for result in results:
        for item in result.missing:
            miss_count[item.part_number] = miss_count.get(item.part_number, 0) + 1
            miss_meta[item.part_number] = (item.part_name, item.node_role)

    lines: list[str] = [
        title,
        f"上游: 冲压价={stamping_price_count}  年度价={annual_price_count}  "
        f"焊接费={welding_count}  包装运输={packaging_count}",
        "",
        "=== 一览（全部 L0）===",
        f"{'#':>3} {'状态':<8} {'零件号':<16} {'月总账':>10} {'间接合计':>10} "
        f"{'总费用':>10} {'缺价':>4} 名称",
        "-" * 100,
    ]
    for index, result in enumerate(results, start=1):
        lines.append(
            f"{index:>3} {result.status:<8} {result.part_number:<16} "
            f"{result.total_amount:>10} {result.indirect_amount:>10} "
            f"{result.grand_total:>10} {len(result.missing):>4} "
            f"{result.part_name or ''}"
        )
    lines.extend(
        [
            "-" * 100,
            f"合计: L0={len(results)}  ok={ok_n}  partial={partial_n}",
            f"月总账: 全部={total_all}  仅 ok={total_ok}",
            f"总费用: 全部={grand_all}  仅 ok={grand_ok}",
            f"月总账分项: 冲压={stamp_sum}  年度/外购={buy_sum}  一口价={bundle_sum}  "
            f"焊接={weld_sum}  焊接其它={other_sum}",
            "",
            "=== 间接费用（一一单列汇总）===",
        ]
    )
    for code, amount in indirect_code_sums.items():
        label = indirect_code_labels.get(code, code)
        lines.append(f"  {label:<12} ({code})  = {amount}")
    lines.append(f"  {'间接费用合计':<12}              = {indirect_sum}")
    lines.extend(
        [
            "",
            f"=== 缺价零件号去重 ({len(miss_count)}) ===",
        ]
    )
    if not miss_count:
        lines.append("（无缺价）")
    else:
        lines.append(f"{'零件号':<16} {'角色':<10} {'出现':>4} 名称")
        for part_number in sorted(miss_count):
            name, role = miss_meta[part_number]
            lines.append(f"{part_number:<16} {role:<10} {miss_count[part_number]:>4} {name or ''}")
    lines.append("")
    return "\n".join(lines)
