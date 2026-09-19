"""准备表 → 价目表汇总。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from app.common.bom.node_order import MISSING_SEQ_NO, bom_node_order_key
from app.common.money import Q4, quantize_money
from app.common.period import is_in_period
from app.exceptions.base import BusinessException
from app.models.bom.node import BomNode
from app.models.bom.procurement_object import BomProcurementObject
from app.services.bom.procurement_object.classify import KIND_L0_DEGENERATE, KIND_L1_STAMPING
from app.services.costing.procurement_contract_report.qty import (
    l0_node_of,
    node_qty,
    vehicle_qty_from_l0,
)

VIEW_PROCUREMENT = "procurement"
VIEW_ASSEMBLY = "assembly"


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
    excel_row: int | None = None
    level: int = 0
    seq_label: str = ""


def prep_fields_from_node(
    node: object | None, *, fallback_excel_row: int | None = None
) -> tuple[int, int | None, int]:
    """level, excel_row, sort_no。excel_row 缺省时留给 bom_node_order_key 回落到 sort_no。"""
    if node is None:
        return 0, fallback_excel_row, 0
    return (
        int(getattr(node, "level", 0) or 0),
        getattr(node, "excel_row", None),
        int(getattr(node, "sort_no", 0) or 0),
    )


def prep_row_order_key(row: PrepRow) -> tuple[int, int, str, int, str, int, int]:
    return bom_node_order_key(
        seq_no=row.l0_seq_no,
        level=row.level,
        excel_row=row.excel_row,
        part_number=row.part_number,
        sort_no=row.sort_no,
        node_id=row.source_node_id,
    )


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


@dataclass(frozen=True)
class ReportScope:
    location: str
    vehicle_model: str
    bom_version: str | None = None
    snapshot_id: int | None = None
    view: str = VIEW_PROCUREMENT
    qa_passed: bool = True
    qa_error_text: str | None = None


@dataclass
class ReportBundle:
    scope: ReportScope
    months: list[tuple[int, int]]
    prep_rows: list[PrepRow]
    price_rows: list[PriceRow]
    missing_month_cell_count: int
    supplier_names: list[str]
    supplier_name: str | None
    vehicle_total: Decimal | None = None
    vehicle_total_skipped: int = 0


def l0_hits_month(l0: BomNode | None, year: int, month: int) -> bool:
    """签约账期只认所属 L0 树根四列；无 L0 则不出。"""
    if l0 is None:
        return False
    return is_in_period(
        effective_year=l0.effective_year,
        effective_month=l0.effective_month,
        expiry_year=l0.expiry_year,
        expiry_month=l0.expiry_month,
        as_of_year=year,
        as_of_month=month,
    )


def l0_hits_any_month(l0: BomNode | None, months: list[tuple[int, int]]) -> bool:
    return any(l0_hits_month(l0, year, month) for year, month in months)


def build_prep_rows(
    objects: list[BomProcurementObject],
    nodes_by_id: dict[int, BomNode],
    months: list[tuple[int, int]],
    costs: dict[tuple[int, int, int], Decimal],
) -> list[PrepRow]:
    """准备表：整窗都不命中所属 L0 的对象行不出；未命中月金额强制 /。"""
    rows: list[PrepRow] = []
    for item in objects:
        node = nodes_by_id.get(item.source_node_id)
        l0 = l0_node_of(item.source_node_id, nodes_by_id)
        if not l0_hits_any_month(l0, months):
            continue
        l0_node_id = l0.id if l0 is not None else item.source_node_id
        l0_seq_no = l0.seq_no if l0 is not None else None
        level, excel_row, sort_no = prep_fields_from_node(node, fallback_excel_row=item.excel_row)
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
                excel_row=excel_row,
                level=level,
                vehicle_qty=vehicle_qty_from_l0(item.source_node_id, nodes_by_id),
                month_amounts=_month_amounts(item.source_node_id, months, costs, l0=l0),
            )
        )
    assign_seq_labels(rows)
    return rows


def build_assembly_prep_rows(
    roots: list[BomNode],
    months: list[tuple[int, int]],
    costs: dict[tuple[int, int, int], Decimal],
) -> list[PrepRow]:
    """树根一行：序号只写 seq_no，用量取根自身 qty，工装靠 object_kind 空 → /。

    只收窗口内至少命中一个月的 L0；未命中月金额强制 /。
    """
    rows: list[PrepRow] = []
    for node in roots:
        if not l0_hits_any_month(node, months):
            continue
        seq_no = node.seq_no
        level, excel_row, sort_no = prep_fields_from_node(node)
        rows.append(
            PrepRow(
                source_node_id=node.id,
                part_number=node.part_number,
                part_name=node.part_name,
                internal_number=node.internal_number,
                supplier_name=None,
                object_kind=None,
                l0_node_id=node.id,
                l0_part_number=node.part_number,
                l0_seq_no=seq_no,
                sort_no=sort_no,
                excel_row=excel_row,
                level=level,
                vehicle_qty=node_qty(node),
                month_amounts=_month_amounts(node.id, months, costs, l0=node),
                seq_label="" if seq_no is None else str(seq_no),
            )
        )
    return rows


def _month_amounts(
    source_node_id: int,
    months: list[tuple[int, int]],
    costs: dict[tuple[int, int, int], Decimal],
    *,
    l0: BomNode | None,
) -> list[MonthAmount]:
    return [
        MonthAmount(
            year=year,
            month=month,
            should_cost=(
                costs.get((year, month, source_node_id)) if l0_hits_month(l0, year, month) else None
            ),
        )
        for year, month in months
    ]


def format_procurement_seq_label(
    *,
    object_kind: str | None,
    l0_seq_no: int | None,
    index_in_group: int,
) -> str:
    """采购协议序号：退化供货件只写 seq_no；其余 `{seq_no}-{组内顺序}`。"""
    if object_kind == KIND_L0_DEGENERATE:
        return "" if l0_seq_no is None else str(l0_seq_no)
    prefix = "" if l0_seq_no is None else str(l0_seq_no)
    return f"{prefix}-{index_in_group}" if prefix else str(index_in_group)


def assign_seq_labels(rows: list[PrepRow]) -> None:
    grouped: dict[int, list[PrepRow]] = defaultdict(list)
    for row in rows:
        grouped[row.l0_node_id].append(row)
    for group in grouped.values():
        group.sort(key=prep_row_order_key)
        for index, row in enumerate(group, start=1):
            row.seq_label = format_procurement_seq_label(
                object_kind=row.object_kind,
                l0_seq_no=row.l0_seq_no,
                index_in_group=index,
            )


def seq_sort_key(seq_label: str) -> tuple[int, int]:
    """序号：总成序号、组内顺序。空号排最后。"""
    text = (seq_label or "").strip()
    if not text:
        return (MISSING_SEQ_NO, MISSING_SEQ_NO)
    if "-" in text:
        head, tail = text.split("-", 1)
        return (_parse_seq_part(head), _parse_seq_part(tail))
    return (_parse_seq_part(text), 0)


def report_sort_key(
    location: str,
    vehicle_model: str,
    seq_label: str,
) -> tuple[str, str, int, int]:
    """基地 → 项目 → 序号。"""
    return (location, vehicle_model, *seq_sort_key(seq_label))


def _parse_seq_part(raw: str) -> int:
    try:
        return int(raw)
    except ValueError:
        return MISSING_SEQ_NO


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
        group.sort(key=prep_row_order_key)
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
