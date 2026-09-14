"""成品核价零件短码与外购件总成判定（无 ORM）。"""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.common.bom.manufacturing_category import (
    short_part_number_digits,
    short_weld_part_number,
)

_FASTENER_NAME_RE = re.compile(r"螺母|螺栓|螺钉|螺柱|铆钉|卡扣|卡子|垫圈|垫片|卡箍")
_FASTENER_PN_RE = re.compile(r"^(N|Q|QR|FQ)", re.I)
_PURCHASED_SOURCES = frozenset({"annual", "bundle", "skipped_by_bundle"})

# 核算报告「说明」、计算过程焊装章共用。前端收起说明读 VO.welding.message，勿再抄字面量。
PURCHASED_ASSEMBLY_NOTE = "年度零件价已含子件和焊装，不再拆算"


def is_purchased_assembly_root(source_node_id: int | None, items: Iterable[object]) -> bool:
    """本卡根是否外购件总成（P4）。

    判定：材料行 ``cost_source=bundle`` 且 ``bom_node_id`` = 本卡 ``source_node_id``。
    walk 只在「有子件且命中年度价」时给**当前节点**写 bundle，所以卡根出现
    这一行，等价于「本件按年度价结算，子孙已含」。

    改行为前读 ``docs/costing/assembly-costing-design.md`` P4。不要改回
    「卡根有年度价仍拆子件」：子件没有独立价会被误报缺价
    （例：青岛 T28 · 502003968AA / 502003966AA）。

    无子件的卡根命中年度价是叶子 ``annual``，本函数为 False，仍抄本卡焊接。
    """
    if source_node_id is None:
        return False
    return any(
        getattr(item, "cost_source", None) == "bundle"
        and getattr(item, "bom_node_id", None) == source_node_id
        for item in items
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


def card_short_code(*, part_number: str | None, level: int | None, view: str) -> str:
    """封面 / 例外：财务按 level，采购册数字末四位。"""
    if view == "procurement":
        return procurement_part_short_code(part_number=part_number) or (part_number or "")
    return part_short_code(part_number=part_number, level=level) or (part_number or "")


def uses_full_part_number(
    *,
    part_number: str | None,
    part_name: str | None,
    supply_type: str | None,
    cost_source: str | None,
) -> bool:
    """外购标准件/紧固件末四位没有采购含义，树节点用全码。"""
    if cost_source not in _PURCHASED_SOURCES:
        return False
    if (supply_type or "").strip() == "标准件":
        return True
    if part_name and _FASTENER_NAME_RE.search(part_name):
        return True
    number = (part_number or "").strip()
    return bool(number and _FASTENER_PN_RE.match(number))


def tree_item_short_code(
    *,
    part_number: str | None,
    part_name: str | None,
    supply_type: str | None,
    cost_source: str | None,
    level: int | None,
    view: str,
) -> str:
    """构成树短码：紧固件全码，其余按财务/采购册规则。"""
    if uses_full_part_number(
        part_number=part_number,
        part_name=part_name,
        supply_type=supply_type,
        cost_source=cost_source,
    ):
        return (part_number or "").strip()
    return card_short_code(part_number=part_number, level=level, view=view)
