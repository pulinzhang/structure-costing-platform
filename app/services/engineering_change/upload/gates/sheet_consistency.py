"""本本 Excel 零件号自洽：确认表号、变更后零件必须出现在材料清单。"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from app.common.engineering_change_gates import (
    EC_AFTER_PART_NOT_ON_BOM,
    EC_PROCESS_NOT_ON_BOM,
    listed,
    unique_texts,
)
from app.exceptions.base import BusinessException
from app.parsers.bom.bom_parser import BomParsedNode
from app.parsers.engineering_change.change_order_parser import ChangeOrderRowParsed


def validate_workbook_part_numbers(
    *,
    bom_nodes: Sequence[BomParsedNode],
    process_part_numbers: Iterable[str],
    change_orders: Sequence[ChangeOrderRowParsed],
) -> None:
    """
    确认表零件号、变更单已填的变更后零件都必须在本本材料清单。
    缺号一次报完。空变更后零件（完成停止、此件不装、总成改图）不查。
    """
    pool = {number for number in unique_texts(node.part_number for node in bom_nodes)}
    missing_process = [
        number for number in unique_texts(process_part_numbers) if number not in pool
    ]
    missing_after = [
        number
        for number in unique_texts(order.after_part_number for order in change_orders)
        if number not in pool
    ]
    parts: list[str] = []
    if missing_process:
        parts.append(
            f"{EC_PROCESS_NOT_ON_BOM}：{listed(missing_process)}。"
            "请把这些号写进「车身件材料清单」，或从「冲压工艺确认表」删掉多出来的号，改完再传。"
        )
    if missing_after:
        parts.append(
            f"{EC_AFTER_PART_NOT_ON_BOM}：{listed(missing_after)}。"
            "请把这些号写进「车身件材料清单」后再传。"
        )
    if parts:
        raise BusinessException(" ".join(parts))
