"""布点导入：模具重量与外形核对重量相对差。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.common.measures import MM3_G_PER_CM3_TO_TON, PERCENT
from app.common.money import Q4, format_money, quantize_money

WEIGHT_RELATIVE_LIMIT = Decimal("0.10")
ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class DieWeightCheckRow:
    part_number: str
    process_seq: str
    excel_row: int | None
    die_length: Decimal | None
    die_width: Decimal | None
    die_height: Decimal | None
    hollow_factor: Decimal | None
    estimated_weight_t: Decimal | None


@dataclass(frozen=True, slots=True)
class DieWeightMismatch:
    part_number: str
    process_seq: str
    excel_row: int | None
    estimated_weight_t: Decimal
    check_weight_t: Decimal
    relative_gap: Decimal | None


def calc_die_weight_t(
    *,
    die_length: Decimal | None,
    die_width: Decimal | None,
    die_height: Decimal | None,
    hollow_factor: Decimal | None,
    density: Decimal,
) -> Decimal | None:
    """外形核对重量（吨）= 长×宽×高×掏空系数×密度 / 10^9。缺尺寸则 None。"""
    if (
        die_length is None
        or die_width is None
        or die_height is None
        or hollow_factor is None
        or density is None
    ):
        return None
    if die_length <= ZERO or die_width <= ZERO or die_height <= ZERO:
        return None
    if hollow_factor < ZERO or density <= ZERO:
        return None
    raw = die_length * die_width * die_height * hollow_factor * density / MM3_G_PER_CM3_TO_TON
    return quantize_money(raw, Q4, allow_negative=False)


def find_die_weight_mismatches(
    rows: Sequence[DieWeightCheckRow],
    *,
    density: Decimal,
) -> list[DieWeightMismatch]:
    """有完整外形且有模具重量时，相对差 > 10% 记一条。缺长宽高/掏空则跳过。"""
    issues: list[DieWeightMismatch] = []
    for row in rows:
        stored = row.estimated_weight_t
        if stored is None:
            continue
        checked = calc_die_weight_t(
            die_length=row.die_length,
            die_width=row.die_width,
            die_height=row.die_height,
            hollow_factor=row.hollow_factor,
            density=density,
        )
        if checked is None:
            continue
        stored_q = quantize_money(stored, Q4, allow_negative=False)
        if stored_q == ZERO:
            if checked == ZERO:
                continue
            issues.append(
                DieWeightMismatch(
                    part_number=row.part_number.strip(),
                    process_seq=str(row.process_seq).strip(),
                    excel_row=row.excel_row,
                    estimated_weight_t=stored_q,
                    check_weight_t=checked,
                    relative_gap=None,
                )
            )
            continue
        gap = abs(stored_q - checked) / stored_q
        if gap > WEIGHT_RELATIVE_LIMIT:
            issues.append(
                DieWeightMismatch(
                    part_number=row.part_number.strip(),
                    process_seq=str(row.process_seq).strip(),
                    excel_row=row.excel_row,
                    estimated_weight_t=stored_q,
                    check_weight_t=checked,
                    relative_gap=gap,
                )
            )
    issues.sort(
        key=lambda item: (
            item.part_number,
            item.process_seq,
            item.excel_row if item.excel_row is not None else 10**9,
        )
    )
    return issues


def format_die_weight_mismatch_issues(issues: Sequence[DieWeightMismatch]) -> str:
    if not issues:
        return ""
    lines = [
        "上传失败：模具重量与外形核对超差（相对差 > 10%），"
        "核对重量 = 长×宽×高×掏空系数×密度÷10^9。"
        f"共 {len(issues)} 道工序，导入已拒绝，未改已有布点：",
    ]
    for item in issues:
        row_bit = f"，Excel 第 {item.excel_row} 行" if item.excel_row else ""
        stored_text = format_money(item.estimated_weight_t, Q4, 4)
        checked_text = format_money(item.check_weight_t, Q4, 4)
        if item.relative_gap is None:
            gap_text = "相对差无法计算（模具重量为 0）"
        else:
            percent_text = format_money(item.relative_gap * PERCENT, Decimal("0.01"), 2)
            gap_text = f"相对差 {percent_text}%"
        lines.append(
            f"零件 {item.part_number} 工序 {item.process_seq}{row_bit}："
            f"模具重量 {stored_text} T，核对重量 {checked_text} T，{gap_text}"
        )
    return "\n".join(lines)
