"""准备表 → 价目表汇总。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from app.common.money import Q4, quantize_money
from app.exceptions.base import BusinessException
from app.models.bom.node import BomNode
from app.models.bom.procurement_object import BomProcurementObject, BomProcurementObjectList
from app.services.bom.procurement_object.classify import KIND_L0_DEGENERATE, KIND_L1_STAMPING
from app.services.costing.procurement_contract_report.qty import l0_node_of, vehicle_qty_from_l0


@dataclass
class MonthAmount:
    year: int
    month: int
    should_cost: Decimal | None


@dataclass
class PrepRow:
    source_node_id: int
    part_number: str
    part_name: str | None
    internal_number: str | None
    supplier_name: str | None
    object_kind: str | None
    l0_node_id: int
    l0_part_number: str
    l0_seq_no: int | None
    sort_no: int
    vehicle_qty: Decimal
    month_amounts: list[MonthAmount]
    seq_label: str = ""


@dataclass(frozen=True)
class ToolingAmounts:
    alloc_price: Decimal | None
    tooling_fee: Decimal | None
    alloc_qty: Decimal | None


@dataclass
class PriceRow:
    seq_label: str
    internal_number: str | None
    part_number: str
    part_name: str | None
    vehicle_qty: Decimal
    object_kind: str | None
    first_l0_part_number: str
    month_amounts: list[MonthAmount]
    tooling_alloc_price: Decimal | None
    tooling_fee: Decimal | None
    tooling_alloc_qty: Decimal | None
    supplier_names: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class ReportBundle:
    header: BomProcurementObjectList
    months: list[tuple[int, int]]
    prep_rows: list[PrepRow]
    price_rows: list[PriceRow]
    missing_month_cell_count: int
    supplier_names: list[str]
    supplier_name: str | None
    vehicle_total: Decimal | None = None
    vehicle_total_skipped: int = 0


def build_prep_rows(
    objects: list[BomProcurementObject],
    nodes_by_id: dict[int, BomNode],
    months: list[tuple[int, int]],
    costs: dict[tuple[int, int, int], Decimal],
) -> list[PrepRow]:
    rows: list[PrepRow] = []
    for item in objects:
        node = nodes_by_id.get(item.source_node_id)
        l0 = l0_node_of(item.source_node_id, nodes_by_id)
        l0_node_id = l0.id if l0 is not None else item.source_node_id
        l0_seq_no = l0.seq_no if l0 is not None else None
        sort_no = node.sort_no if node is not None else (item.excel_row or 0)
        month_amounts = [
            MonthAmount(
                year=year,
                month=month,
                should_cost=costs.get((year, month, item.source_node_id)),
            )
            for year, month in months
        ]
        rows.append(
            PrepRow(
                source_node_id=item.source_node_id,
                part_number=item.part_number,
                part_name=item.part_name,
                internal_number=item.internal_number,
                supplier_name=item.supplier_name,
                object_kind=item.object_kind,
                l0_node_id=l0_node_id,
                l0_part_number=item.l0_part_number,
                l0_seq_no=l0_seq_no,
                sort_no=sort_no,
                vehicle_qty=vehicle_qty_from_l0(item.source_node_id, nodes_by_id),
                month_amounts=month_amounts,
            )
        )
    assign_seq_labels(rows)
    return rows


def assign_seq_labels(rows: list[PrepRow]) -> None:
    grouped: dict[int, list[PrepRow]] = defaultdict(list)
    for row in rows:
        grouped[row.l0_node_id].append(row)
    for group in grouped.values():
        group.sort(key=lambda row: (row.sort_no, row.source_node_id))
        for index, row in enumerate(group, start=1):
            if row.object_kind == KIND_L0_DEGENERATE:
                row.seq_label = "" if row.l0_seq_no is None else str(row.l0_seq_no)
                continue
            prefix = "" if row.l0_seq_no is None else str(row.l0_seq_no)
            row.seq_label = f"{prefix}-{index}" if prefix else str(index)


_SEQ_MISSING = 10**9


def seq_sort_key(seq_label: str) -> tuple[int, int]:
    """序号：总成序号、组内顺序。空号排最后。"""
    text = (seq_label or "").strip()
    if not text:
        return (_SEQ_MISSING, _SEQ_MISSING)
    if "-" in text:
        head, tail = text.split("-", 1)
        return (_parse_seq_part(head), _parse_seq_part(tail))
    return (_parse_seq_part(text), 0)


def report_sort_key(
    location: str,
    vehicle_model: str,
    bom_version: str,
    seq_label: str,
) -> tuple[str, str, str, int, int]:
    """基地 → 项目 → 版本 → 序号。"""
    return (location, vehicle_model, bom_version, *seq_sort_key(seq_label))


def _parse_seq_part(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        return _SEQ_MISSING


def aggregate_price_rows(
    prep_rows: list[PrepRow],
    months: list[tuple[int, int]],
    tooling_by_part: dict[str, ToolingAmounts],
) -> list[PriceRow]:
    grouped: dict[str, list[PrepRow]] = defaultdict(list)
    for row in prep_rows:
        grouped[row.part_number].append(row)

    price_rows: list[PriceRow] = []
    for part_number, group in grouped.items():
        group.sort(key=lambda row: (row.sort_no, row.source_node_id))
        first = group[0]
        month_amounts = [
            MonthAmount(
                year=year,
                month=month,
                should_cost=_unique_month_price(part_number, year, month, group),
            )
            for year, month in months
        ]
        suppliers = tuple(dict.fromkeys(row.supplier_name for row in group if row.supplier_name))
        object_kind = first.object_kind
        tooling = tooling_by_part.get(part_number, _EMPTY_TOOLING)
        if object_kind != KIND_L1_STAMPING:
            tooling = _EMPTY_TOOLING
        price_rows.append(
            PriceRow(
                seq_label=first.seq_label,
                internal_number=first.internal_number,
                part_number=part_number,
                part_name=first.part_name,
                vehicle_qty=sum((row.vehicle_qty for row in group), Decimal("0")),
                object_kind=object_kind,
                first_l0_part_number=first.l0_part_number,
                month_amounts=month_amounts,
                tooling_alloc_price=tooling.alloc_price,
                tooling_fee=tooling.tooling_fee,
                tooling_alloc_qty=tooling.alloc_qty,
                supplier_names=suppliers,
            )
        )
    return price_rows


def _unique_month_price(
    part_number: str,
    year: int,
    month: int,
    group: list[PrepRow],
) -> Decimal | None:
    found: list[tuple[int, Decimal]] = []
    for row in group:
        amount = next(
            (
                cell.should_cost
                for cell in row.month_amounts
                if cell.year == year and cell.month == month
            ),
            None,
        )
        if amount is not None:
            found.append((row.source_node_id, amount))
    unique_values = {price for _node_id, price in found}
    if len(unique_values) > 1:
        detail = "、".join(f"节点 {node_id}={price}" for node_id, price in found)
        raise BusinessException(
            f"零件号 {part_number} 在 {year}年{month}月 存在多个结算价格：{detail}。"
            "请核对该零件总成采购视图后重算。"
        )
    if not unique_values:
        return None
    return next(iter(unique_values))


_EMPTY_TOOLING = ToolingAmounts(alloc_price=None, tooling_fee=None, alloc_qty=None)
_WAN_TO_PIECE = Decimal("10000")


def resolve_tooling(
    *,
    object_kind: str | None,
    part_number: str,
    die_fees: dict[str, tuple[Decimal, Decimal]],
    gauge_fees: dict[str, tuple[Decimal, Decimal]],
) -> ToolingAmounts:
    if object_kind != KIND_L1_STAMPING:
        return _EMPTY_TOOLING
    die_row = die_fees.get(part_number)
    gauge_row = gauge_fees.get(part_number)

    die_per_piece: Decimal | None = None
    die_total: Decimal | None = None
    alloc_qty: Decimal | None = None
    if die_row is not None:
        die_per_piece, die_qty_wan = die_row
        if die_qty_wan > 0:
            alloc_qty = die_qty_wan * _WAN_TO_PIECE
            die_total = die_per_piece * alloc_qty

    gauge_per_piece: Decimal | None = None
    gauge_total: Decimal | None = None
    if gauge_row is not None:
        gauge_fee_wan, gauge_qty_wan = gauge_row
        gauge_total = gauge_fee_wan * _WAN_TO_PIECE
        if gauge_qty_wan > 0:
            gauge_per_piece = gauge_fee_wan / gauge_qty_wan

    pieces: list[Decimal] = []
    if die_per_piece is not None:
        pieces.append(die_per_piece)
    if gauge_per_piece is not None:
        pieces.append(gauge_per_piece)
    alloc_price = (
        quantize_money(sum(pieces, Decimal("0")), Q4, allow_negative=True) if pieces else None
    )

    totals: list[Decimal] = []
    if die_total is not None:
        totals.append(die_total)
    if gauge_total is not None:
        totals.append(gauge_total)
    tooling_fee = (
        quantize_money(sum(totals, Decimal("0")), Q4, allow_negative=True) if totals else None
    )
    if alloc_price is None and tooling_fee is None and alloc_qty is None:
        return _EMPTY_TOOLING
    return ToolingAmounts(
        alloc_price=alloc_price,
        tooling_fee=tooling_fee,
        alloc_qty=alloc_qty,
    )


def count_missing_month_cells(prep_rows: list[PrepRow]) -> int:
    return sum(1 for row in prep_rows for cell in row.month_amounts if cell.should_cost is None)


def sum_vehicle_total(
    price_rows: list[PriceRow],
    months: list[tuple[int, int]],
) -> tuple[Decimal | None, int]:
    """窗口内各月：各零件 单车数量 × 当月结算价格 之和；无结算价的月不计入。"""
    if not months:
        return None, 0
    month_set = set(months)
    total = Decimal("0")
    used = 0
    skipped = 0
    for row in price_rows:
        contributed = False
        for cell in row.month_amounts:
            if (cell.year, cell.month) not in month_set or cell.should_cost is None:
                continue
            total += row.vehicle_qty * cell.should_cost
            contributed = True
        if contributed:
            used += 1
        else:
            skipped += 1
    if used == 0:
        return None, skipped
    return quantize_money(total, Q4, allow_negative=True), skipped
