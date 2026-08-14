"""冲压零件核价共用工具（Service / Export 共享，避免双份默认值与符号漂移）。"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

# 与 SettingsService / 系统配置缺省一致
DEFAULT_STEEL_DENSITY = Decimal("7.85")
DEFAULT_MATERIAL_LOSS_RATE = Decimal("0.003")
DEFAULT_SCRAP_RECOVERY_RATE = Decimal("0.97")


def location_candidates(location: str) -> list[str]:
    """兼容「青岛」与「青岛基地」。"""
    loc = (location or "").strip()
    if not loc:
        return []
    candidates = [loc]
    if loc.endswith("基地"):
        candidates.append(loc[:-2])
    else:
        candidates.append(f"{loc}基地")
    return list(dict.fromkeys(candidates))


def to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def format_number(value: Any, digits: int | None = None) -> float | str:
    if value is None:
        return ""
    number = float(value)
    if digits is None:
        return number
    return round(number, digits)


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
        parts.append(f"净价{format_number(net, 2)}")
    if market is not None:
        parts.append(f"大盘{format_number(market, 2)}")
    if deduction is not None:
        parts.append(f"扣费{format_number(deduction, 2)}")
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
            lines.append(f"{label}: {format_number(fee_val, 3)}")
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
