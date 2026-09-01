"""
BOM 焊接信息原文拆解（纯函数）

将 weld_info 文本拆成多种工艺的单件过程量，并映射标准工艺名称
（WeldingStandardProcessName，与焊接单价 item_name 对齐）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from app.common.bom.welding_standard_process import (
    resolve_standard_process_name,
    resolve_standard_process_unit,
)


@dataclass(frozen=True)
class WeldingProcessBreakdownParsedItem:
    """单条工艺拆解结果（单件口径）"""

    process_token: str
    process_qty: Decimal
    process_qty_unit: str
    matched_span: str
    process_qty_secondary: Decimal | None = None
    process_qty_secondary_unit: str | None = None
    standard_process_name: str | None = None
    standard_process_unit: str | None = None
    map_status: str = "unmapped"
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class WeldingProcessBreakdownParseResult:
    """一段 weld_info 的拆解结果"""

    items: list[WeldingProcessBreakdownParsedItem]
    parse_status: str  # ok / partial / unparsed
    tags: tuple[str, ...] = ()
    normalized_text: str = ""


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None


def _normalize_weld_info_text(raw: str) -> str:
    """
    归一化特殊字符，降低原文写法差异对拆解的影响。

    - 全角/半角冒号、括号、加号旁空格
    - 异体字 黒 → 黑
    - m² / ㎡ → m2
    - 连续空白压成单空格
    """
    text = raw.strip()
    text = text.replace("黒", "黑")
    text = text.replace("ｍ", "m").replace("Ｍ", "M")
    text = text.replace("㎡", "m2").replace("m²", "m2").replace("M2", "m2")
    # 冒号两侧：保留「名称：数字」语义，统一为全角冒号便于阅读；匹配仍兼容半角
    text = re.sub(r"[:：]", "：", text)
    # 材料清单笔误「凸焊:：2」→「凸焊：2」
    text = re.sub(r"(：\s*)+", "：", text)
    # 电泳+喷粉 中间多余空格
    text = re.sub(r"\+\s*", "+", text)
    text = re.sub(r"\s+", " ", text)
    return text


def parse_welding_info_text(weld_info: str | None) -> WeldingProcessBreakdownParseResult:
    """
    拆解焊接信息原文。

    兼容例：
      焊点：99 凸焊：7 涂胶：1550mm
      焊点:23个 焊缝：3条（60mm)   ← 半角冒号 + 括号半全角混用
      凸焊:1 / 植焊:2
      塞焊：3个（90mm）
      黒漆件 电泳面积：0.017m2  → 标准工艺默认「电泳（盐雾试验要求≤244H）」
      电泳黑漆：0.098m2           → 同上（材料清单常见省略「面积」）
      凸焊:：2                   → 连续冒号压成「凸焊：2」
      铆接：1 电泳+ 喷粉（黑色） 面积：0.014m2  → 「面积」一律按电泳
    """
    raw = (weld_info or "").strip()
    if not raw:
        return WeldingProcessBreakdownParseResult(
            items=[], parse_status="unparsed", normalized_text=""
        )

    text = _normalize_weld_info_text(raw)

    tags: list[str] = []
    if re.search(r"电泳", text):
        tags.append("电泳")
    if re.search(r"喷粉", text):
        tags.append("喷粉")
    if re.search(r"黑漆", text):
        tags.append("黑漆件")
    if re.search(r"电镀", text):
        tags.append("电镀")

    # 括号允许 （ ) ( ） 混用；mm 大小写；冒号已归一为 ：
    patterns: list[tuple[str, str, str]] = [
        (r"焊点：?\s*(\d+)\s*个?", "焊点", "个"),
        (r"凸焊：?\s*(\d+)\s*个?", "凸焊", "个"),
        (r"植焊：?\s*(\d+)\s*个?", "植焊", "个"),
        (r"铆接：?\s*(\d+)\s*个?", "铆接", "个"),
        (
            r"塞焊：?\s*(\d+)\s*个?\s*[（(]?\s*(\d+(?:\.\d+)?)\s*[mM]{2}\s*[）)]?",
            "塞焊",
            "个",
        ),
        (
            r"弧焊：?\s*(\d+)\s*条\s*[（(]\s*(\d+(?:\.\d+)?)\s*[mM]{2}\s*[）)]",
            "弧焊",
            "条",
        ),
        (
            r"焊缝：?\s*(\d+)\s*条\s*[（(]\s*(\d+(?:\.\d+)?)\s*[mM]{2}\s*[）)]",
            "焊缝",
            "条",
        ),
        (r"涂胶：?\s*(\d+(?:\.\d+)?)\s*[mM]{2}", "涂胶", "mm"),
        (r"电泳面积：?\s*([\d.]+)\s*m2", "电泳面积", "m2"),
        (r"电泳黑漆：?\s*([\d.]+)\s*m2", "电泳面积", "m2"),
        (r"电泳：?\s*([\d.]+)\s*m2", "电泳面积", "m2"),
        (r"(?<!电泳)面积：?\s*([\d.]+)\s*m2", "面积", "m2"),
    ]

    items: list[WeldingProcessBreakdownParsedItem] = []
    covered_spans: list[tuple[int, int]] = []

    for pattern, token, unit in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            span = match.span()
            if any(not (span[1] <= start or span[0] >= end) for start, end in covered_spans):
                continue
            qty = _to_decimal(match.group(1))
            if qty is None:
                continue
            secondary = None
            secondary_unit = None
            if match.lastindex and match.lastindex >= 2 and match.group(2):
                secondary = _to_decimal(match.group(2))
                if secondary is not None:
                    secondary_unit = "mm"
            standard_name, map_status = resolve_standard_process_name(token, tags=tuple(tags))
            items.append(
                WeldingProcessBreakdownParsedItem(
                    process_token=token,
                    process_qty=qty,
                    process_qty_unit=unit,
                    matched_span=match.group(0),
                    process_qty_secondary=secondary,
                    process_qty_secondary_unit=secondary_unit,
                    standard_process_name=standard_name,
                    standard_process_unit=resolve_standard_process_unit(standard_name),
                    map_status=map_status,
                    tags=tuple(tags),
                )
            )
            covered_spans.append(span)

    items.sort(key=lambda item: text.find(item.matched_span))

    if items:
        parse_status = "ok"
    elif tags:
        parse_status = "partial"
    else:
        parse_status = "unparsed"

    return WeldingProcessBreakdownParseResult(
        items=items,
        parse_status=parse_status,
        tags=tuple(tags),
        normalized_text=text,
    )
