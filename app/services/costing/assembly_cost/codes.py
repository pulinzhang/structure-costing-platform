"""成品核价零件短码（无 ORM）。"""

from app.common.bom.manufacturing_category import (
    short_part_number_digits,
    short_weld_part_number,
)


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
