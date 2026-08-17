"""焊接计费用量：辅助量优先 + 与单价单位换算。

业务约定（与 L0 核对导出说明一致）：
- 有 ``process_qty_secondary``（辅助量）时以其计费，否则用过程量
- 长度：mm / cm 互转（1 cm = 10 mm）；例：52mm → 单价单位 CM 为 5.2
- 面积：平方 / 平方米 / m2 / ㎡ 视为同一量纲（系数 1）
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.common.money import Q4, quantize_money

# 长度：统一换算到 mm
_LENGTH_TO_MM: dict[str, Decimal] = {
    "mm": Decimal("1"),
    "cm": Decimal("10"),
    "m": Decimal("1000"),
}

_AREA_KEYS = frozenset({"平方", "m2"})
_COUNT_KEYS = frozenset({"个"})


def normalize_unit_key(unit: str | None) -> str:
    """单位规范化键（比较 / 换算用）。"""
    raw = (unit or "").strip()
    if not raw:
        return ""
    text = (
        raw.replace("㎡", "m2")
        .replace("m²", "m2")
        .replace("M²", "m2")
        .replace("Ｍ", "m")
    )
    lower = text.lower()
    if lower in _LENGTH_TO_MM:
        return lower
    if lower == "m2":
        return "m2"
    if text in {"平方"} or lower == "平方":
        return "平方"
    if text in {"平方米", "平米"} or lower in {"平方米", "平米"}:
        return "m2"
    if lower in {"个", "pcs", "pc", "件"} or text == "个":
        return "个"
    return lower


def convert_qty_to_unit(
    qty: Decimal,
    *,
    from_unit: str | None,
    to_unit: str | None,
) -> Decimal:
    """将用量换算到目标单位；不兼容时抛 ``ValueError``。"""
    source = normalize_unit_key(from_unit)
    target = normalize_unit_key(to_unit)
    amount = qty if isinstance(qty, Decimal) else Decimal(str(qty))

    if not source and not target:
        return quantize_money(amount, Q4)
    if source == target:
        return quantize_money(amount, Q4)
    if source in _LENGTH_TO_MM and target in _LENGTH_TO_MM:
        qty_mm = amount * _LENGTH_TO_MM[source]
        return quantize_money(qty_mm / _LENGTH_TO_MM[target], Q4)
    if source in _AREA_KEYS and target in _AREA_KEYS:
        return quantize_money(amount, Q4)
    if source in _COUNT_KEYS and target in _COUNT_KEYS:
        return quantize_money(amount, Q4)
    raise ValueError(f"单位无法换算：{from_unit or '空'} → {to_unit or '空'}")


def resolve_raw_billing_qty(line: Any) -> tuple[Decimal, str, str]:
    """
    取计费原始用量（未换算到单价单位）。

    返回 ``(qty, unit, source)``，``source`` 为 ``secondary`` | ``primary``。
    """
    secondary = getattr(line, "process_qty_secondary", None)
    if secondary is not None:
        unit = (getattr(line, "process_qty_secondary_unit", None) or "").strip()
        return Decimal(str(secondary)), unit, "secondary"
    primary = getattr(line, "process_qty", None)
    if primary is None:
        raise ValueError("过程量缺失")
    unit = (getattr(line, "process_qty_unit", None) or "").strip()
    return Decimal(str(primary)), unit, "primary"


def resolve_billing_qty_for_price(
    line: Any,
    *,
    price_unit: str | None,
) -> tuple[Decimal, str, str]:
    """
    计费用量（辅助量优先）并换算到单价单位。

    返回 ``(billing_qty, billing_unit, remark)``。
    """
    raw_qty, raw_unit, source = resolve_raw_billing_qty(line)
    display_price_unit = (price_unit or "").strip() or raw_unit
    converted = convert_qty_to_unit(
        raw_qty,
        from_unit=raw_unit,
        to_unit=display_price_unit or raw_unit,
    )
    source_label = "辅助量" if source == "secondary" else "过程量"
    raw_u = raw_unit or "—"
    price_u = display_price_unit or "—"
    raw_q = quantize_money(raw_qty, Q4)
    if normalize_unit_key(raw_unit) == normalize_unit_key(display_price_unit):
        remark = f"计费={source_label} {raw_q}{raw_u}"
    else:
        remark = f"计费={source_label} {raw_q}{raw_u} → {converted}{price_u}"
    return converted, display_price_unit, remark
