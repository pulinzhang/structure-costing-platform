"""
BOM 单元格值解析工具

纯函数，无状态，易于单元测试。
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


_EMPTY_MARKERS = {"", "/", "／", "-", "—", "无"}


def cell_value(ws: Any, row: int, col: int) -> Any:
    return ws.cell(row, col).value


def to_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    if text in _EMPTY_MARKERS:
        return None
    return text


def is_filled(value: Any) -> bool:
    return to_text(value) is not None


def parse_seq_no(value: Any) -> int | None:
    """
    解析 A 列序号。

    仅接受整数（含 Excel 数值型）；空值或非数字返回 None。
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return None
    text = to_text(value)
    if not text:
        return None
    if not re.fullmatch(r"\d+", text):
        return None
    return int(text)


def to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    text = to_text(value)
    if not text:
        return None
    cleaned = text.replace(",", "").replace("kg", "").replace("KG", "").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_qty(value: Any) -> tuple[Decimal | None, str, str | None]:
    """返回 (qty, qty_unit, qty_text)。"""
    text = to_text(value)
    if text is None:
        return None, "pcs", None
    lower = text.lower().replace(" ", "")
    if lower.endswith("mm"):
        num = to_decimal(lower[:-2])
        return num, "mm", text
    num = to_decimal(text)
    if num is not None:
        return num, "pcs", text
    return None, "pcs", text


def parse_thickness(value: Any) -> tuple[Decimal | None, str | None]:
    text = to_text(value)
    if text is None:
        return None, None
    match = re.search(r"(?i)t\s*=\s*([0-9]+(?:\.[0-9]+)?)", text)
    if match:
        return Decimal(match.group(1)), text
    # 纯数字也当作料厚
    num = to_decimal(text)
    if num is not None and "m" not in text.lower() and "x" not in text.lower():
        return num, text
    return None, text


def parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = to_text(value)
    if not text:
        return None
    for pattern in (
        r"(\d{4})[年./-](\d{1,2})[月./-](\d{1,2})",
        r"(\d{4})[年./-](\d{1,2})月?",
    ):
        match = re.search(pattern, text)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            day = int(match.group(3)) if match.lastindex and match.lastindex >= 3 else 1
            try:
                return date(year, month, day)
            except ValueError:
                return None
    return None
