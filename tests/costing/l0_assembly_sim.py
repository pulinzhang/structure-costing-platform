"""
成品（L0）月核价 — 只读模拟（测试 / 验收用）

规则对齐 docs/l0-assembly-costing-design.md：
  L0 → L1 →（有子件则）L2
  叶子取价：
    1) 完整零件号 → 冲压价（stamping_part_costs.unit_cost；
       = 直接成本 + 财务/管理/仓储包装/税前利润等费率金额）
    2) 完整零件号 → 年度价
    3) 仍找不到且零件号含「-」→ 取「-」之前作为零件号，仅在冲压价表回退
  L1 有子件且年度价命中 → 一口价剪枝；否则拆散 rollup
  最后 + L0 焊接费（+ other_fee）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

Money = Decimal
_Q4 = Decimal("0.0001")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(_Q4, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class SimBomNode:
    """BOM 节点（模拟入参，与 ORM 解耦）。"""

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
    """L0 焊接费（模拟入参）。"""

    final_amount: Decimal
    other_fee: Decimal = Decimal("0")
    missing_price_count: int = 0


@dataclass(frozen=True)
class SimLine:
    """参与计价的一行。"""

    level_label: str
    part_number: str
    source: Literal["stamping", "annual", "bundle"]
    unit_price: Decimal
    effective_qty: Decimal
    line_amount: Decimal


@dataclass(frozen=True)
class SimMissing:
    part_number: str
    part_name: str | None
    node_role: str
    effective_qty: Decimal


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
    missing: list[SimMissing] = field(default_factory=list)
    lines: list[SimLine] = field(default_factory=list)


def base_part_number_before_dash(part_number: str) -> str | None:
    """取第一个「-」之前的内容；无「-」则返回 None。"""
    if "-" not in part_number:
        return None
    base = part_number.split("-", 1)[0].strip()
    return base or None


def _lookup_leaf_price(
    part_number: str,
    stamping_prices: dict[str, Decimal],
    annual_prices: dict[str, Decimal],
) -> tuple[Literal["stamping", "annual"] | None, Decimal | None]:
    if part_number in stamping_prices:
        return "stamping", stamping_prices[part_number]
    if part_number in annual_prices:
        return "annual", annual_prices[part_number]
    # 完整号双表都无：用「-」前零件号仅回退冲压价（例 551001730AA-1 → 551001730AA）
    base = base_part_number_before_dash(part_number)
    if base is not None and base in stamping_prices:
        return "stamping", stamping_prices[base]
    return None, None


def simulate_l0(
    l0: SimBomNode,
    children_by_parent: dict[int | None, list[SimBomNode]],
    stamping_prices: dict[str, Decimal],
    annual_prices: dict[str, Decimal],
    welding: SimWeldingFee | None,
) -> L0SimResult:
    """对单个成品做 L0→L1→L2 rollup 模拟。"""
    stamp = Decimal("0")
    purchased = Decimal("0")
    bundle = Decimal("0")
    lines: list[SimLine] = []
    missing: list[SimMissing] = []

    l1_nodes = sorted(children_by_parent.get(l0.id, []), key=lambda n: n.sort_no)

    for l1 in l1_nodes:
        l1_qty = l1.qty if l1.qty is not None else Decimal("1")
        l2_nodes = sorted(children_by_parent.get(l1.id, []), key=lambda n: n.sort_no)

        if l2_nodes:
            if l1.part_number in annual_prices:
                unit = annual_prices[l1.part_number]
                line_amount = quantize_money(unit * l1_qty)
                bundle += line_amount
                lines.append(
                    SimLine(
                        level_label="L1-bundle",
                        part_number=l1.part_number,
                        source="bundle",
                        unit_price=unit,
                        effective_qty=l1_qty,
                        line_amount=line_amount,
                    )
                )
                continue

            for l2 in l2_nodes:
                l2_qty = l2.qty if l2.qty is not None else Decimal("1")
                effective_qty = l1_qty * l2_qty
                source, unit = _lookup_leaf_price(
                    l2.part_number, stamping_prices, annual_prices
                )
                if source is None or unit is None:
                    missing.append(
                        SimMissing(
                            part_number=l2.part_number,
                            part_name=l2.part_name,
                            node_role=l2.node_role,
                            effective_qty=effective_qty,
                        )
                    )
                    continue
                line_amount = quantize_money(unit * effective_qty)
                if source == "stamping":
                    stamp += line_amount
                else:
                    purchased += line_amount
                lines.append(
                    SimLine(
                        level_label="L2",
                        part_number=l2.part_number,
                        source=source,
                        unit_price=unit,
                        effective_qty=effective_qty,
                        line_amount=line_amount,
                    )
                )
            continue

        source, unit = _lookup_leaf_price(l1.part_number, stamping_prices, annual_prices)
        if source is None or unit is None:
            missing.append(
                SimMissing(
                    part_number=l1.part_number,
                    part_name=l1.part_name,
                    node_role=l1.node_role,
                    effective_qty=l1_qty,
                )
            )
            continue
        line_amount = quantize_money(unit * l1_qty)
        if source == "stamping":
            stamp += line_amount
        else:
            purchased += line_amount
        lines.append(
            SimLine(
                level_label="L1-leaf",
                part_number=l1.part_number,
                source=source,
                unit_price=unit,
                effective_qty=l1_qty,
                line_amount=line_amount,
            )
        )

    if welding is None:
        weld_amount = Decimal("0")
        other_fee = Decimal("0")
        weld_incomplete = True
    else:
        weld_amount = welding.final_amount
        other_fee = welding.other_fee
        weld_incomplete = welding.missing_price_count > 0

    total = quantize_money(stamp + purchased + bundle + weld_amount + other_fee)
    status: Literal["ok", "partial"] = (
        "ok" if (not missing and not weld_incomplete) else "partial"
    )

    return L0SimResult(
        part_number=l0.part_number,
        part_name=l0.part_name,
        status=status,
        stamping_amount=quantize_money(stamp),
        purchased_amount=quantize_money(purchased),
        bundle_amount=quantize_money(bundle),
        welding_amount=quantize_money(weld_amount),
        other_fee=quantize_money(other_fee),
        total_amount=total,
        missing=missing,
        lines=lines,
    )


def simulate_all_l0(
    nodes: list[SimBomNode],
    stamping_prices: dict[str, Decimal],
    annual_prices: dict[str, Decimal],
    welding_by_part: dict[str, SimWeldingFee],
) -> list[L0SimResult]:
    """对清单内全部 L0 成品模拟。"""
    children_by_parent: dict[int | None, list[SimBomNode]] = {}
    for node in nodes:
        children_by_parent.setdefault(node.parent_id, []).append(node)

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
        )
        for l0 in l0_nodes
    ]


def format_simulation_report(
    results: list[L0SimResult],
    *,
    title: str,
    stamping_price_count: int,
    annual_price_count: int,
    welding_count: int,
) -> str:
    """生成可读中文统计（一览 / 缺价 / 分项）。"""
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

    miss_count: dict[str, int] = {}
    miss_meta: dict[str, tuple[str | None, str]] = {}
    for result in results:
        for item in result.missing:
            miss_count[item.part_number] = miss_count.get(item.part_number, 0) + 1
            miss_meta[item.part_number] = (item.part_name, item.node_role)

    lines: list[str] = [
        title,
        f"上游: 冲压价={stamping_price_count}  年度价={annual_price_count}  焊接费={welding_count}",
        "",
        "=== 一览（全部 L0）===",
        f"{'#':>3} {'状态':<8} {'零件号':<16} {'冲压':>10} {'年度/外购':>10} "
        f"{'一口价':>8} {'焊接':>8} {'合计':>10} {'缺价':>4} 名称",
        "-" * 100,
    ]
    for index, result in enumerate(results, start=1):
        lines.append(
            f"{index:>3} {result.status:<8} {result.part_number:<16} "
            f"{result.stamping_amount:>10} {result.purchased_amount:>10} "
            f"{result.bundle_amount:>8} {result.welding_amount:>8} "
            f"{result.total_amount:>10} {len(result.missing):>4} "
            f"{result.part_name or ''}"
        )
    lines.extend(
        [
            "-" * 100,
            f"合计: L0={len(results)}  ok={ok_n}  partial={partial_n}",
            f"金额: 全部行合计(含 partial 已命中)={total_all}  仅 ok 成品={total_ok}",
            f"分项: 冲压={stamp_sum}  年度/外购={buy_sum}  一口价={bundle_sum}  "
            f"焊接={weld_sum}  其它={other_sum}",
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
            lines.append(
                f"{part_number:<16} {role:<10} {miss_count[part_number]:>4} {name or ''}"
            )
    lines.append("")
    return "\n".join(lines)
