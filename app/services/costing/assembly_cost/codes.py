"""成品核价零件短码（无 ORM）。"""

from app.common.bom.manufacturing_category import (
    short_part_number_digits,
    short_weld_part_number,
)


def part_short_code(*, part_number: str | None, level: int | None) -> str:
    """财务册：L0 数字末四位；分总成带 -N 时保留字母尾。"""
    if int(level or 0) == 0:
        return short_part_number_digits(part_number) or ""
    return short_weld_part_number(part_number) or ""


def procurement_part_short_code(*, part_number: str | None) -> str:
    """采购册「零件」短码：与列表列一致，数字末四位（不按分总成保留 -N）。"""
    return short_part_number_digits(part_number) or ""


def item_short_code(
    *,
    part_number: str | None,
    cost_source: str | None,
) -> str:
    """子件短码只给冲压零件价，数字末四位；标准件/年度价留空。"""
    if cost_source != "stamping":
        return ""
    return short_part_number_digits(part_number) or ""
