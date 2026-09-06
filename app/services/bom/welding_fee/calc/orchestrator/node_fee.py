"""单 L0 焊接费明细（公式原样迁出指挥类）。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.common.bom.welding_billing_qty import resolve_billing_qty_for_price
from app.common.money import Q4, quantize_money
from app.models.bom import BomWeldingProcessBreakdownNode
from app.models.bom.welding_unit_price import BomWeldingUnitPrice
from app.schemas.dto.bom_welding_fee_dto import BomWeldingFeeItemPayload

MATCH_MATCHED = "matched"
MATCH_MISSING_PRICE = "missing_price"
MATCH_UNMAPPED = "unmapped"

CALC_OK = "ok"
CALC_PARTIAL = "partial"
CALC_FAILED = "failed"

MAP_READY = "ready"


@dataclass(slots=True)
class NodeFeeCalcParts:
    process_line_count: int
    matched_line_count: int
    missing_price_count: int
    total_welding_fee: Decimal
    calc_status: str
    calc_message: str | None
    items: list[BomWeldingFeeItemPayload]


def calc_node_fee(
    node: BomWeldingProcessBreakdownNode,
    price_map: dict[str, BomWeldingUnitPrice],
) -> NodeFeeCalcParts:
    lines = list(node.lines or [])
    items: list[BomWeldingFeeItemPayload] = []
    matched_count = 0
    missing_count = 0
    total_fee = Decimal("0")

    for line in lines:
        item = BomWeldingFeeItemPayload(
            line_no=line.line_no,
            process_token=line.process_token,
            standard_process_name=line.standard_process_name,
            process_qty=quantize_money(line.process_qty, Q4),
            process_qty_unit=line.process_qty_unit,
            unit_price=None,
            unit=None,
            line_fee=None,
            match_status=MATCH_UNMAPPED,
            source_breakdown_line_id=line.id,
            remark=None,
        )

        name = (line.standard_process_name or "").strip()
        is_ready = (line.map_status or "") == MAP_READY and bool(name)
        if not is_ready:
            if not name:
                item.remark = "未映射标准工艺"
            else:
                item.remark = f"映射未就绪({line.map_status})"
            items.append(item)
            continue

        price_row = price_map.get(name)
        if price_row is None:
            item.match_status = MATCH_MISSING_PRICE
            item.remark = f"未找到单价：{name}"
            missing_count += 1
            items.append(item)
            continue

        try:
            billing_qty, billing_unit, billing_remark = resolve_billing_qty_for_price(
                line,
                price_unit=price_row.unit,
            )
        except ValueError as error:
            item.match_status = MATCH_UNMAPPED
            item.remark = str(error)
            items.append(item)
            continue

        unit_price = quantize_money(price_row.unit_price, Q4)
        line_fee = quantize_money(billing_qty * unit_price, Q4)
        item.process_qty = billing_qty
        item.process_qty_unit = billing_unit
        item.unit_price = unit_price
        item.unit = price_row.unit
        item.line_fee = line_fee
        item.match_status = MATCH_MATCHED
        item.remark = billing_remark
        matched_count += 1
        total_fee += line_fee
        items.append(item)

    process_line_count = len(lines)
    total_fee = quantize_money(total_fee, Q4)

    if process_line_count == 0:
        calc_status = CALC_FAILED
        calc_message = "无焊接工艺明细"
    elif missing_count == 0 and matched_count > 0:
        calc_status = CALC_OK
        calc_message = None
    elif matched_count > 0 and missing_count > 0:
        calc_status = CALC_PARTIAL
        calc_message = f"部分缺单价（匹配 {matched_count}，缺价 {missing_count}）"
    elif missing_count > 0 and matched_count == 0:
        calc_status = CALC_FAILED
        calc_message = f"全部缺单价（{missing_count} 行）"
    else:
        calc_status = CALC_FAILED
        calc_message = "无可用标准工艺映射"

    return NodeFeeCalcParts(
        process_line_count=process_line_count,
        matched_line_count=matched_count,
        missing_price_count=missing_count,
        total_welding_fee=total_fee,
        calc_status=calc_status,
        calc_message=calc_message,
        items=items,
    )
