"""单道工序计算依据文案。"""

from __future__ import annotations

from decimal import Decimal

from app.services.stamping.process_fee.calc.constants import (
    TONNAGE_SOURCE_INHERITED,
    TONNAGE_SOURCE_SWING_SHEAR,
)


def build_process_basis_text(
    *,
    process_label: str,
    tonnage_source: str,
    resolved_tonnage: int | None,
    cost_ratio: Decimal | None,
    price_per_stroke: Decimal | None,
    line_fee: Decimal,
    inherited_from_part_number: str | None = None,
    inherited_from_process_seq: str | None = None,
    inherited_from_process_code: str | None = None,
) -> str:
    """生成单道工序人可读计算依据。"""
    if tonnage_source == TONNAGE_SOURCE_SWING_SHEAR:
        from_part = (inherited_from_part_number or "").strip()
        if from_part:
            from_seq = (inherited_from_process_seq or "").strip() or "?"
            from_code = (inherited_from_process_code or "").strip()
            from_label = f"{from_seq}/{from_code}" if from_code else from_seq
            return (
                f"{process_label}: 继承上一件{from_part}/{from_label} "
                f"摆剪不计费 = 0"
            )
        return f"{process_label}: 摆剪不计费 = 0"

    ratio_text = f"{cost_ratio:.2f}" if cost_ratio is not None else "1.00"
    price_text = (
        f"{price_per_stroke:.3f}" if price_per_stroke is not None else "-"
    )
    fee_text = f"{line_fee:.3f}"
    tonnage_text = f"{resolved_tonnage}T" if resolved_tonnage is not None else "-"

    if tonnage_source == TONNAGE_SOURCE_INHERITED:
        from_seq = (inherited_from_process_seq or "").strip() or "?"
        from_code = (inherited_from_process_code or "").strip()
        from_label = f"{from_seq}/{from_code}" if from_code else from_seq
        from_part = inherited_from_part_number or "?"
        return (
            f"{process_label}: 继承上一件{from_part}/{from_label} "
            f"{tonnage_text} × 比例{ratio_text} × 单价{price_text} = {fee_text}"
        )

    return (
        f"{process_label}: 自有 {tonnage_text} × 比例{ratio_text} "
        f"× 单价{price_text} = {fee_text}"
    )
