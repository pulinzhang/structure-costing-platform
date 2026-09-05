"""零件短码与焊费行收集。"""

from app.common.bom.manufacturing_category import (
    short_part_number_digits,
    short_weld_part_number,
)
from app.models.costing.assembly_cost import AssemblyCost


def part_short_code(*, part_number: str | None, level: int | None) -> str:
    """L0 数字末四位；分总成带 -N 时保留字母尾。"""
    if int(level or 0) == 0:
        return short_part_number_digits(part_number) or ""
    return short_weld_part_number(part_number) or ""


def item_short_code(
    *,
    part_number: str | None,
    level: int | None,
    cost_source: str | None,
) -> str:
    """子件短码只给冲压零件价；标准件/年度价不截四位。"""
    if cost_source != "stamping":
        return ""
    return part_short_code(part_number=part_number, level=level)


def collect_welding_fee_ids(records: list[AssemblyCost]) -> list[int]:
    """导出卡实际抄到的焊费行，去重保序。"""
    seen: dict[int, None] = {}
    for record in records:
        fee_id = record.welding_fee_id
        if fee_id is None:
            continue
        seen[int(fee_id)] = None
    return list(seen)
