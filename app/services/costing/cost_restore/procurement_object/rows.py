"""把一张采购对象卡展开成普通明细行。只读已落库数字，不重算。"""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal
from typing import TypeVar

from app.common.money import Q4, optional_format_money, quantize_money
from app.models.bom.welding_fee import BomWeldingFee
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.assembly_cost_item import AssemblyCostItem
from app.models.costing.stamping_part_cost import StampingPartCost
from app.models.stamping.die import StampingDieProcess
from app.models.stamping.die_fee import StampingDieFee
from app.models.stamping.die_fee_item import StampingDieFeeItem
from app.models.stamping.process_fee import StampingProcessFee
from app.models.stamping.process_fee_item import StampingProcessFeeItem
from app.models.stamping.tailor_weld_blank import StampingTailorWeldBlank
from app.schemas.vo.cost_restore_procurement_object_vo import CostRestoreLineVO

_T = TypeVar("_T")

MISMATCH = "还原不符"
RECORD_GONE = "记录已不存在"
NO_WELD_RECORD = "无焊接核算记录"
OTHER_FEE_NOTE = "结算价中另计一次"
NO_CARD = "没有总成核价卡"
THOUSAND = Decimal("1000")

_STATUS_LABEL = {
    "success": "成功",
    "partial": "部分成功",
    "failed": "失败",
}


@dataclass
class ObjectHit:
    object_id: int
    supplier_name: str | None
    vehicle_model: str
    object_kind_label: str
    internal_number: str | None
    part_number: str
    part_name: str | None
    vehicle_qty: Decimal
    level: int
    source_node_id: int
    excel_filename: str = ""
    excel_sheet_name: str = ""
    excel_row: int = 0


@dataclass
class RestoreBundle:
    part_costs: dict[tuple[str, str], list[StampingPartCost]]
    process_fees: dict[int, StampingProcessFee]
    die_fees: dict[int, StampingDieFee]
    die_processes: dict[int, StampingDieProcess]
    welding_fees: dict[int, BomWeldingFee]
    blanks_by_part_id: dict[int, list[StampingTailorWeldBlank]]


@dataclass
class RestoreLine:
    object_id: int
    row_type: str
    supplier_name: str | None = None
    vehicle_model: str | None = None
    object_kind: str | None = None
    internal_number: str | None = None
    object_part_number: str | None = None
    object_part_name: str | None = None
    vehicle_qty: Decimal | None = None
    settlement_price: Decimal | None = None
    leaf_part_number: str | None = None
    priced_part_number: str | None = None
    sheet_length: Decimal | None = None
    sheet_width: Decimal | None = None
    thickness: Decimal | None = None
    parts_per_sheet: int | None = None
    blank_weight_kg: Decimal | None = None
    material: str | None = None
    finished_weight_kg: Decimal | None = None
    utilization_pct: Decimal | None = None
    scrap_weight_kg: Decimal | None = None
    scrap_price_per_kg: Decimal | None = None
    swing_shear_fee_per_ton: Decimal | None = None
    steel_price_per_kg: Decimal | None = None
    material_amount_sheet: Decimal | None = None
    loss_scrap_deduction: Decimal | None = None
    process_scrap_deduction: Decimal | None = None
    material_net: Decimal | None = None
    automation: str | None = None
    process_code: str | None = None
    tonnage: int | None = None
    stroke_fee: Decimal | None = None
    die_length: Decimal | None = None
    die_width: Decimal | None = None
    die_height: Decimal | None = None
    hollow_factor: Decimal | None = None
    die_sets: int | None = None
    die_weight_t: Decimal | None = None
    material_cost: Decimal | None = None
    process_cost: Decimal | None = None
    material_plus_process: Decimal | None = None
    die_fee: Decimal | None = None
    gauge_fee: Decimal | None = None
    finance_fee: Decimal | None = None
    management_fee: Decimal | None = None
    warehouse_fee: Decimal | None = None
    profit_fee: Decimal | None = None
    direct_cost: Decimal | None = None
    unit_cost: Decimal | None = None
    line_amount: Decimal | None = None
    outsourced_amount: Decimal | None = None
    weld_name: str | None = None
    weld_qty: Decimal | None = None
    weld_unit_price: Decimal | None = None
    weld_amount: Decimal | None = None
    ecoat_amount: Decimal | None = None
    part_cost_id: int | None = None
    process_fee_id: int | None = None
    die_fee_id: int | None = None
    gauge_fee_id: int | None = None
    steel_price_id: int | None = None
    scrap_price_id: int | None = None
    welding_fee_id: int | None = None
    source_filename: str | None = None
    source_row: int | None = None
    calc_status: str | None = None
    remark: str | None = None


def money_sum(values: list[Decimal | int | None]) -> Decimal:
    total = Decimal("0")
    for value in values:
        total += Decimal(value or 0)
    return total


def same_money(left: Decimal | int | None, right: Decimal | int | None) -> bool:
    return quantize_money(Decimal(left or 0), Q4) == quantize_money(Decimal(right or 0), Q4)


def join_notes(*parts: str | None) -> str | None:
    texts = [part for part in parts if part]
    return "；".join(texts) or None


def priced_part_number(part_number: str, match_hint: str | None) -> str:
    hint = (match_hint or "").strip()
    if hint.startswith("dash_fallback:"):
        priced = hint.split(":", 1)[1].strip()
        return priced or part_number
    return part_number


def pick_part_cost(
    candidates: list[StampingPartCost],
    unit_price: Decimal | None,
) -> tuple[StampingPartCost | None, str | None]:
    """单价相同任取一条。单价不同且对不上明细单价时，材料与工序留空。"""
    if not candidates:
        return None, RECORD_GONE
    matched = [row for row in candidates if same_money(row.unit_cost, unit_price)]
    if matched:
        return matched[0], None
    prices = {
        (getattr(row, "stamping_supplier", None) or "未标工厂", quantize_money(row.unit_cost, Q4))
        for row in candidates
    }
    if len(prices) == 1:
        return candidates[0], None
    listed = "、".join(f"{name} {price}" for name, price in sorted(prices))
    return None, f"各工厂单价：{listed}"


def slice_objects(items: list[_T], page: int, size: int) -> list[_T]:
    start = (page - 1) * size
    return items[start : start + size]


def line_to_vo(line: RestoreLine) -> CostRestoreLineVO:
    payload: dict[str, object] = {}
    for field in fields(line):
        value = getattr(line, field.name)
        if isinstance(value, Decimal):
            payload[field.name] = optional_format_money(value, Q4, 4)
        elif isinstance(value, int) and not isinstance(value, bool):
            payload[field.name] = optional_format_money(Decimal(value), Q4, 4)
        else:
            payload[field.name] = value
    return CostRestoreLineVO.model_validate(payload)


def build_object_lines(
    hit: ObjectHit,
    card: AssemblyCost | None,
    bundle: RestoreBundle,
) -> list[RestoreLine]:
    if card is None:
        return [_identity(hit, None, "合计", remark=NO_CARD)]
    lines: list[RestoreLine] = []
    stamping_lines: list[RestoreLine] = []
    other_lines: list[RestoreLine] = []
    for item in sorted(card.items or [], key=lambda row: row.sort_no):
        source = item.cost_source
        if source == "stamping":
            stamping_lines.extend(_stamping_leaf(hit, card, item, bundle))
        elif source == "annual":
            other_lines.append(
                _amount_row(hit, card, item, "外购", item.line_amount, item.match_hint)
            )
        elif source == "bundle":
            other_lines.append(
                _amount_row(hit, card, item, "一口价", item.line_amount, item.match_hint)
            )
        elif source == "skipped_by_bundle":
            other_lines.append(
                _amount_row(
                    hit,
                    card,
                    item,
                    "被一口价包含",
                    Decimal("0"),
                    join_notes("包在上级零件", item.match_hint),
                )
            )
        elif source == "missing":
            other_lines.append(_amount_row(hit, card, item, "缺价", None, item.match_hint))
    weld_rows = _welding_rows(hit, card, bundle)
    lines.extend(stamping_lines)
    lines.extend(other_lines)
    lines.extend(weld_rows)
    lines.append(_total_row(hit, card, stamping_lines, weld_rows))
    return lines


def _identity(
    hit: ObjectHit,
    card: AssemblyCost | None,
    row_type: str,
    **extras: object,
) -> RestoreLine:
    line = RestoreLine(
        object_id=hit.object_id,
        row_type=row_type,
        supplier_name=hit.supplier_name,
        vehicle_model=hit.vehicle_model,
        object_kind=hit.object_kind_label,
        internal_number=hit.internal_number,
        object_part_number=hit.part_number,
        object_part_name=hit.part_name,
        vehicle_qty=hit.vehicle_qty,
        settlement_price=None if card is None else card.total_amount,
    )
    for key, value in extras.items():
        setattr(line, key, value)
    return line


def _stamping_leaf(
    hit: ObjectHit,
    card: AssemblyCost,
    item: AssemblyCostItem,
    bundle: RestoreBundle,
) -> list[RestoreLine]:
    priced = priced_part_number(item.part_number, item.match_hint)
    candidates = bundle.part_costs.get((hit.vehicle_model, priced), [])
    cost, pick_note = pick_part_cost(candidates, item.unit_price)
    fallback_note = None
    if priced != item.part_number:
        fallback_note = f"取价零件号 {priced}"
    if cost is None:
        blank = _identity(
            hit,
            card,
            row_type="材料",
            leaf_part_number=item.part_number,
            priced_part_number=priced,
            remark=join_notes(pick_note, fallback_note),
        )
        subtotal = _subtotal_without_cost(hit, card, item, join_notes(pick_note, fallback_note))
        return [blank, subtotal]
    rows = _material_rows(hit, card, item, cost, bundle, fallback_note)
    rows.extend(_process_rows(hit, card, item, cost, bundle))
    rows.append(_leaf_subtotal(hit, card, item, cost, rows))
    return rows


def _material_rows(
    hit: ObjectHit,
    card: AssemblyCost,
    item: AssemblyCostItem,
    cost: StampingPartCost,
    bundle: RestoreBundle,
    fallback_note: str | None,
) -> list[RestoreLine]:
    blanks = bundle.blanks_by_part_id.get(cost.source_part_id, [])
    if not blanks:
        return [_material_row(hit, card, item, cost, fallback_note, show_cost=True)]
    rows: list[RestoreLine] = []
    for index, blank in enumerate(blanks):
        rows.append(
            _material_row(
                hit,
                card,
                item,
                cost,
                fallback_note if index == 0 else None,
                show_cost=index == 0,
                blank=blank,
            )
        )
    return rows


def _material_row(
    hit: ObjectHit,
    card: AssemblyCost,
    item: AssemblyCostItem,
    cost: StampingPartCost,
    extra_note: str | None,
    *,
    show_cost: bool,
    blank: StampingTailorWeldBlank | None = None,
) -> RestoreLine:
    offal = cost.is_offal_nested
    formula_note = None
    if show_cost and not offal:
        expected = (
            (cost.material_amount_sheet or 0)
            - (cost.loss_scrap_deduction or 0)
            - (cost.process_scrap_deduction or 0)
        )
        if cost.material_net_per_part is not None and not same_money(
            expected, cost.material_net_per_part
        ):
            formula_note = MISMATCH
    swing = cost.swing_shear_fee_per_ton if cost.has_swing_shear else None
    steel_kg = None
    if cost.steel_ton_price is not None:
        steel_kg = (cost.steel_ton_price + (cost.swing_shear_fee_per_ton or 0)) / THOUSAND
    scrap_kg = None if cost.scrap_ton_price is None else cost.scrap_ton_price / THOUSAND
    length = blank.sheet_length if blank is not None else cost.sheet_length
    width = blank.sheet_width if blank is not None else cost.sheet_width
    thickness = blank.thickness if blank is not None else cost.thickness
    material = blank.material if blank is not None else cost.material
    leaf_number = item.part_number
    if blank is not None:
        leaf_number = blank.blank_part_number
    return _identity(
        hit,
        card,
        row_type="材料",
        leaf_part_number=leaf_number,
        priced_part_number=priced_part_number(item.part_number, item.match_hint),
        sheet_length=length,
        sheet_width=width,
        thickness=thickness,
        parts_per_sheet=None if blank is not None else cost.parts_per_sheet,
        blank_weight_kg=None if blank is not None else cost.blank_weight_kg,
        material=material,
        finished_weight_kg=None if blank is not None else cost.finished_total_kg,
        utilization_pct=None if blank is not None else cost.material_utilization_pct,
        scrap_weight_kg=None if blank is not None else cost.scrap_weight_kg,
        scrap_price_per_kg=None if not show_cost else scrap_kg,
        swing_shear_fee_per_ton=None if not show_cost else swing,
        steel_price_per_kg=None if not show_cost else steel_kg,
        material_amount_sheet=None if (not show_cost or offal) else cost.material_amount_sheet,
        loss_scrap_deduction=None if (not show_cost or offal) else cost.loss_scrap_deduction,
        process_scrap_deduction=None if (not show_cost or offal) else cost.process_scrap_deduction,
        material_net=cost.material_net_per_part if show_cost else None,
        part_cost_id=cost.id,
        process_fee_id=cost.process_fee_id,
        die_fee_id=cost.die_fee_id,
        gauge_fee_id=cost.gauge_fee_id,
        steel_price_id=cost.steel_price_id,
        scrap_price_id=cost.scrap_price_id,
        source_filename=cost.excel_filename,
        source_row=cost.excel_row,
        remark=join_notes(formula_note, extra_note),
    )


def _process_rows(
    hit: ObjectHit,
    card: AssemblyCost,
    item: AssemblyCostItem,
    cost: StampingPartCost,
    bundle: RestoreBundle,
) -> list[RestoreLine]:
    fee_id = cost.process_fee_id
    if fee_id is None:
        return []
    fee = bundle.process_fees.get(fee_id)
    if fee is None:
        return [
            _identity(
                hit,
                card,
                "工序",
                leaf_part_number=item.part_number,
                automation=cost.automation,
                process_fee_id=fee_id,
                part_cost_id=cost.id,
                remark=RECORD_GONE,
            )
        ]
    die_fee = bundle.die_fees.get(cost.die_fee_id) if cost.die_fee_id else None
    rows: list[RestoreLine] = []
    items = sorted(fee.process_items or [], key=lambda row: (row.process_order or 0, row.id or 0))
    for process in items:
        die_process, die_item = _match_die(die_fee, bundle, process)
        note = None
        if process.tonnage_source == "inherited":
            note = join_notes(
                "继承吨位",
                process.inherited_from_part_number,
                process.inherited_from_process_seq,
                process.inherited_from_process_code,
            )
        if die_item is not None and die_item.source_die_process_id and die_process is None:
            note = join_notes(note, RECORD_GONE)
        rows.append(
            _identity(
                hit,
                card,
                "工序",
                leaf_part_number=item.part_number,
                automation=cost.automation,
                process_code=process.process_code,
                tonnage=process.resolved_tonnage,
                stroke_fee=process.line_fee,
                die_length=None if die_process is None else die_process.die_length,
                die_width=None if die_process is None else die_process.die_width,
                die_height=None if die_process is None else die_process.die_height,
                hollow_factor=None if die_process is None else die_process.hollow_factor,
                die_sets=(
                    die_process.die_sets
                    if die_process is not None
                    else (None if die_item is None else die_item.die_sets)
                ),
                die_weight_t=(
                    die_process.estimated_weight_t
                    if die_process is not None
                    else (None if die_item is None else die_item.estimated_weight_t)
                ),
                part_cost_id=cost.id,
                process_fee_id=fee_id,
                die_fee_id=cost.die_fee_id,
                remark=note,
            )
        )
    return rows


def _match_die(
    die_fee: StampingDieFee | None,
    bundle: RestoreBundle,
    process: StampingProcessFeeItem,
) -> tuple[StampingDieProcess | None, StampingDieFeeItem | None]:
    if die_fee is None:
        return None, None
    chosen = None
    for item in die_fee.items or []:
        if process.process_seq and item.process_seq == process.process_seq:
            chosen = item
            break
    if chosen is None:
        return None, None
    process_row = None
    if chosen.source_die_process_id:
        process_row = bundle.die_processes.get(chosen.source_die_process_id)
    return process_row, chosen


def _extend(amount: Decimal | None, qty: Decimal) -> Decimal:
    return (amount or Decimal("0")) * qty


def _leaf_subtotal(
    hit: ObjectHit,
    card: AssemblyCost,
    item: AssemblyCostItem,
    cost: StampingPartCost,
    detail_rows: list[RestoreLine],
) -> RestoreLine:
    qty = item.effective_qty if item.effective_qty is not None else Decimal("0")
    material_cost = _extend(cost.material_net_per_part, qty)
    process_cost = _extend(cost.process_fee_amount, qty)
    die_fee = _extend(cost.die_fee_amount, qty)
    gauge_fee = _extend(cost.gauge_fee_amount, qty)
    finance_fee = _extend(cost.finished_finance_fee, qty)
    management_fee = _extend(cost.finished_management_fee, qty)
    warehouse_fee = _extend(cost.finished_warehouse_packaging_fee, qty)
    profit_fee = _extend(cost.finished_pretax_profit_fee, qty)
    direct = material_cost + process_cost + die_fee + gauge_fee
    unit_extended = _extend(cost.unit_cost, qty)
    notes: list[str | None] = []
    stroke_sum = money_sum([row.stroke_fee for row in detail_rows if row.row_type == "工序"])
    if cost.process_fee_id and not same_money(stroke_sum, cost.process_fee_amount):
        notes.append(MISMATCH)
    built = (
        (cost.material_net_per_part or 0)
        + (cost.process_fee_amount or 0)
        + (cost.die_fee_amount or 0)
        + (cost.gauge_fee_amount or 0)
        + (cost.finished_finance_fee or 0)
        + (cost.finished_management_fee or 0)
        + (cost.finished_warehouse_packaging_fee or 0)
        + (cost.finished_pretax_profit_fee or 0)
    )
    if not same_money(built, cost.unit_cost) or not same_money(unit_extended, item.line_amount):
        notes.append(MISMATCH)
    return _identity(
        hit,
        card,
        "叶子小计",
        leaf_part_number=item.part_number,
        material_cost=material_cost,
        process_cost=process_cost,
        material_plus_process=material_cost + process_cost,
        die_fee=die_fee,
        gauge_fee=gauge_fee,
        finance_fee=finance_fee,
        management_fee=management_fee,
        warehouse_fee=warehouse_fee,
        profit_fee=profit_fee,
        direct_cost=direct,
        unit_cost=unit_extended,
        line_amount=item.line_amount,
        part_cost_id=cost.id,
        process_fee_id=cost.process_fee_id,
        die_fee_id=cost.die_fee_id,
        gauge_fee_id=cost.gauge_fee_id,
        remark=join_notes(*notes),
    )


def _subtotal_without_cost(
    hit: ObjectHit,
    card: AssemblyCost,
    item: AssemblyCostItem,
    note: str | None,
) -> RestoreLine:
    return _identity(
        hit,
        card,
        "叶子小计",
        leaf_part_number=item.part_number,
        line_amount=item.line_amount,
        remark=join_notes(note, MISMATCH if item.line_amount else None),
    )


def _amount_row(
    hit: ObjectHit,
    card: AssemblyCost,
    item: AssemblyCostItem,
    row_type: str,
    amount: Decimal | None,
    note: str | None,
) -> RestoreLine:
    return _identity(
        hit,
        card,
        row_type,
        leaf_part_number=item.part_number,
        outsourced_amount=amount,
        line_amount=item.line_amount if row_type != "被一口价包含" else Decimal("0"),
        remark=note,
    )


def _welding_rows(hit: ObjectHit, card: AssemblyCost, bundle: RestoreBundle) -> list[RestoreLine]:
    fee_id = card.welding_fee_id
    if not fee_id:
        return [_identity(hit, card, "焊接", weld_amount=Decimal("0"), remark=NO_WELD_RECORD)]
    fee = bundle.welding_fees.get(fee_id)
    if fee is None:
        return [
            _identity(
                hit,
                card,
                "焊接",
                welding_fee_id=fee_id,
                remark=RECORD_GONE,
            )
        ]
    level_note = None
    if fee.level != hit.level:
        level_note = f"焊接层级 {fee.level}，对象层级 {hit.level}"
    rows: list[RestoreLine] = []
    fee_sum = Decimal("0")
    for item in sorted(fee.items or [], key=lambda row: (row.line_no, row.id)):
        name = item.standard_process_name or item.process_token
        is_ecoat = (item.standard_process_name or "").startswith("电泳")
        status_note = None
        if item.match_status in {"unmapped", "missing_price"}:
            status_note = item.match_status
        amount = item.line_fee or Decimal("0")
        fee_sum += amount
        rows.append(
            _identity(
                hit,
                card,
                "焊接",
                weld_name=name,
                weld_qty=item.process_qty,
                weld_unit_price=item.unit_price,
                weld_amount=None if is_ecoat else amount,
                ecoat_amount=amount if is_ecoat else None,
                welding_fee_id=fee_id,
                remark=join_notes(level_note if not rows else None, status_note),
            )
        )
    other = fee.other_fee or Decimal("0")
    sum_note = None if same_money(fee_sum, fee.total_welding_fee) else MISMATCH
    if fee.final_welding_fee is not None and not same_money(
        fee.final_welding_fee, card.welding_amount
    ):
        sum_note = join_notes(sum_note, MISMATCH)
    rows.append(
        _identity(
            hit,
            card,
            "其它费用",
            weld_name="其它费用",
            weld_amount=other,
            welding_fee_id=fee_id,
            remark=join_notes(OTHER_FEE_NOTE, sum_note),
        )
    )
    return rows


def _total_row(
    hit: ObjectHit,
    card: AssemblyCost,
    stamping_lines: list[RestoreLine],
    weld_rows: list[RestoreLine],
) -> RestoreLine:
    subtotals = [row for row in stamping_lines if row.row_type == "叶子小计"]
    material_cost = money_sum([row.material_cost for row in subtotals])
    process_cost = money_sum([row.process_cost for row in subtotals])
    stamping_sum = Decimal("0")
    annual_sum = Decimal("0")
    bundle_sum = Decimal("0")
    for item in card.items or []:
        if item.cost_source == "stamping":
            stamping_sum += item.line_amount or 0
        elif item.cost_source == "annual":
            annual_sum += item.line_amount or 0
        elif item.cost_source == "bundle":
            bundle_sum += item.line_amount or 0
    breaks: list[str] = []
    if not same_money(stamping_sum, card.stamping_amount):
        breaks.append("冲压明细与卡上冲压金额")
    if not same_money(annual_sum, card.purchased_amount):
        breaks.append("年度价与外购金额")
    if not same_money(bundle_sum, card.bundle_amount):
        breaks.append("一口价金额")
    material_parts = stamping_sum + annual_sum + bundle_sum
    if not same_money(material_parts, card.material_amount):
        breaks.append("材料合计")
    status = _STATUS_LABEL.get(card.calc_status, card.calc_status)
    status_note = join_notes(status, card.calc_message)
    mismatch = f"{MISMATCH}：" + "、".join(breaks) if breaks else None
    weld_fee_id = card.welding_fee_id
    return _identity(
        hit,
        card,
        "合计",
        material_cost=material_cost,
        process_cost=process_cost,
        material_plus_process=material_cost + process_cost,
        outsourced_amount=annual_sum + bundle_sum,
        weld_amount=money_sum(
            [
                (row.weld_amount or 0) + (row.ecoat_amount or 0)
                for row in weld_rows
                if row.row_type == "焊接"
            ]
        ),
        line_amount=card.total_amount,
        welding_fee_id=weld_fee_id,
        calc_status=card.calc_status,
        remark=join_notes(mismatch, _weld_tie_note(card), status_note),
    )


def _weld_tie_note(card: AssemblyCost) -> str | None:
    other = card.welding_other_fee or Decimal("0")
    welding = card.welding_amount or Decimal("0")
    total = card.total_amount or Decimal("0")
    material = card.material_amount or Decimal("0")
    breaks: list[str] = []
    if not same_money(material + welding + other, total):
        breaks.append("结算价")
    if not breaks:
        return None
    return f"{MISMATCH}：" + "、".join(breaks)
