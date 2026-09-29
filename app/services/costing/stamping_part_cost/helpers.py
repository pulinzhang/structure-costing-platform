"""冲压零件核价共用工具（Service / Export 共享，避免双份默认值与符号漂移）。"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from app.common.money import (
    Q2,
    Q3,
    Q4,
    Q6,
    excel_money_cell,
    format_money,
    optional_format_money,
)

_DIGITS_TO_QUANT = {
    2: Q2,
    3: Q3,
    4: Q4,
    6: Q6,
}


def to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def join_slash_formatted(
    values: list[Decimal | None],
    quant: Decimal,
    places: int,
) -> str | None:
    """按子片顺序用 / 拼接已量化数值；全空则 None。"""
    texts: list[str] = []
    for value in values:
        text = optional_format_money(value, quant, places)
        if text is not None:
            texts.append(text)
    if not texts:
        return None
    return "/".join(texts)


def format_ton_price_label(value: Decimal) -> str:
    quantized = value.quantize(Q2, rounding=ROUND_HALF_UP)
    if quantized == quantized.to_integral_value():
        return str(int(quantized))
    text = format(quantized, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def join_slash_ton_prices(values: list[Decimal | None]) -> str | None:
    """子片钢材吨价用 / 拼接；缺价用 — 占位以与料厚段对齐。"""
    if not values:
        return None
    labels: list[str] = []
    has_price = False
    for value in values:
        if value is None:
            labels.append("—")
            continue
        has_price = True
        labels.append(format_ton_price_label(value))
    if not has_price:
        return None
    return "/".join(labels)


def format_number(value: Any, digits: int | None = None) -> Decimal | str:
    """Excel 单元格 / 溯源文本用：保持 Decimal，空则空串。"""
    if value is None:
        return ""
    if digits is None:
        return excel_money_cell(value, Q6)
    quant = _DIGITS_TO_QUANT.get(digits, Decimal(10) ** -digits)
    return excel_money_cell(value, quant)


def format_excel_cell_trace(
    *,
    filename: str | None,
    sheet_name: str | None,
    excel_row: int | None,
    excel_col: int | None,
) -> str:
    """单组 Excel 四件套：文件 · 表页 · Rn · Cn。"""
    parts: list[str] = []
    if filename:
        parts.append(str(filename).strip())
    if sheet_name:
        parts.append(str(sheet_name).strip())
    if excel_row is not None:
        parts.append(f"R{excel_row}")
    if excel_col is not None:
        parts.append(f"C{excel_col}")
    return " · ".join(p for p in parts if p)


def format_steel_price_excel_trace(steel: Any) -> str:
    """
    钢材联动价全部 Excel 溯源（基价/厚度/宽度/锌层），不含 ID。
    供人工打开对应文件定位单元格核对。
    """
    if steel is None:
        return ""
    lines: list[str] = []
    for label, prefix in (
        ("基价", "base"),
        ("厚度", "thickness"),
        ("宽度", "width"),
        ("锌层", "zinc"),
    ):
        text = format_excel_cell_trace(
            filename=getattr(steel, f"{prefix}_excel_filename", None),
            sheet_name=getattr(steel, f"{prefix}_sheet_name", None),
            excel_row=getattr(steel, f"{prefix}_excel_row", None),
            excel_col=getattr(steel, f"{prefix}_excel_col", None),
        )
        if text:
            lines.append(f"{label}:{text}")
    return "\n".join(lines)


def format_scrap_price_trace(scrap: Any) -> str:
    """废料月度价人可读定位键（基地·年月·净价）。"""
    if scrap is None:
        return ""
    parts: list[str] = []
    location = (getattr(scrap, "location", None) or "").strip()
    year = getattr(scrap, "year", None)
    month = getattr(scrap, "month", None)
    if location:
        parts.append(location)
    if year is not None and month is not None:
        parts.append(f"{year}年{month}月")
    market = getattr(scrap, "market_price", None)
    deduction = getattr(scrap, "deduction_fee", None)
    net = getattr(scrap, "net_price", None)
    if net is not None:
        parts.append(f"净价{format_money(net, Q2, 2)}")
    if market is not None:
        parts.append(f"大盘{format_money(market, Q2, 2)}")
    if deduction is not None:
        parts.append(f"扣费{format_money(deduction, Q2, 2)}")
    remark = (getattr(scrap, "remark", None) or "").strip()
    if remark:
        parts.append(remark)
    return " · ".join(str(p) for p in parts if p not in ("", None))


def format_process_fee_trace(fee: Any) -> str:
    """加工费溯源：工艺确认表文件名 + 各工序人可读依据。"""
    if fee is None:
        return ""
    lines: list[str] = []
    filename = (getattr(fee, "excel_filename", None) or "").strip()
    if filename:
        lines.append(f"工艺文件:{filename}")
    items = list(getattr(fee, "process_items", None) or [])
    items = sorted(
        items,
        key=lambda item: (
            item.process_order if item.process_order is not None else 10**9,
            item.id or 0,
        ),
    )
    for item in items:
        text = (getattr(item, "basis_text", None) or "").strip()
        if text:
            lines.append(text)
            continue
        seq = (getattr(item, "process_seq", None) or "").strip() or "?"
        code = (getattr(item, "process_code", None) or "").strip()
        label = f"{seq}/{code}" if code else seq
        fee_val = getattr(item, "line_fee", None)
        if fee_val is not None:
            lines.append(f"{label}: {format_money(fee_val, Q3, 3)}")
        else:
            lines.append(label)
    return "\n".join(lines)


def part_excel_row_col(row: Any) -> str:
    """零件工艺表行列：R6C2。"""
    excel_row = getattr(row, "excel_row", None)
    excel_col = getattr(row, "excel_part_col", None)
    text = ""
    if excel_row is not None:
        text += f"R{excel_row}"
    if excel_col is not None:
        text += f"C{excel_col}"
    return text
