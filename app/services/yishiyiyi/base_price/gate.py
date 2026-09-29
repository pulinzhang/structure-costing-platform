"""基准价写入门禁。

调用方先按年月取出行。这里只定两把钥匙，不要和表唯一键混成一把：
- 中标：基地 + 牌号。一个月只能有一个钢厂，参考厚度可以有多条。
- 月度涨跌：基地 + 牌号 + 参考厚度 + 参考宽度。钢厂优先对同一家；
  上月这一规格只有一条时，钢厂换了也对照那一条。
表唯一键更宽，含钢厂、类别、厚度、宽度。不要改成上面这两条。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.common.money import Q2
from app.exceptions import BusinessException


@dataclass(frozen=True, slots=True)
class AwardLine:
    """一条待写入或已在库中的中标记录。厚度或宽度为空表示参考规格没有解析出来。"""

    location: str
    grade: str
    steel_mill: str
    thick: Decimal | None
    width: Decimal | None = None
    category_name: str = ""
    processing_fee: Decimal | None = None
    base_price: Decimal | None = None
    excel_row: int | None = None


def winning_mill_key(line: AwardLine) -> tuple[str, str]:
    """同一个月内的中标身份：基地 + 牌号。"""
    return (line.location, line.grade)


def month_move_key(line: AwardLine) -> tuple[str, str, Decimal, Decimal] | None:
    """上月涨跌身份：基地 + 牌号 + 参考厚度 + 参考宽度。规格不全则无法对照。"""
    if line.thick is None or line.width is None:
        return None
    return (
        line.location,
        line.grade,
        line.thick.quantize(Q2, rounding=ROUND_HALF_UP),
        line.width.quantize(Q2, rounding=ROUND_HALF_UP),
    )


def reject_invalid_base_price_award(
    incoming: list[AwardLine],
    existing: list[AwardLine],
    *,
    max_thickness: Decimal,
) -> None:
    """
    整批拒绝，不写库。
    基准厚度或参考宽度为空则拒绝。
    料厚大于配置的车身件上限（默认 3.00 mm）则拒绝；等于上限允许。
    同一基地、同一牌号在本次或与库内合并后出现多家中标钢厂则拒绝。
    同一钢厂、不同参考厚度仍然放行。
    """
    violations = _spec_texts(incoming, max_thickness)
    violations.extend(_multiple_mill_texts(incoming, existing))
    if not violations:
        return
    raise BusinessException("没有保存。" + sample_text(violations))


def _spec_texts(incoming: list[AwardLine], max_thickness: Decimal) -> list[str]:
    limit = max_thickness.quantize(Q2, rounding=ROUND_HALF_UP)
    texts: list[str] = []
    for line in incoming:
        prefix = f"{_row_prefix(line)}{line.location} {line.grade}："
        if line.thick is None:
            texts.append(f"{prefix}参考规格的厚度是空的，应写成如 1.0*1250")
            continue
        if line.width is None:
            texts.append(f"{prefix}参考规格的宽度是空的，应写成如 1.0*1250")
            continue
        thick = line.thick.quantize(Q2, rounding=ROUND_HALF_UP)
        if thick > limit:
            texts.append(
                f"{prefix}参考厚度 {thick:.2f} mm，大于设置中的车身件料厚上限 {limit:.2f} mm。"
                "请改规格，或到系统设置的「基准价」里调高上限"
            )
    return texts


def _multiple_mill_texts(incoming: list[AwardLine], existing: list[AwardLine]) -> list[str]:
    incoming_mills: dict[tuple[str, str], set[str]] = {}
    for line in incoming:
        incoming_mills.setdefault(winning_mill_key(line), set()).add(line.steel_mill)
    existing_mills: dict[tuple[str, str], set[str]] = {}
    for line in existing:
        existing_mills.setdefault(winning_mill_key(line), set()).add(line.steel_mill)

    texts: list[str] = []
    for key in sorted(incoming_mills):
        location, grade = key
        current = incoming_mills[key]
        stored = existing_mills.get(key, set())
        if len(current | stored) <= 1:
            continue
        current_text = "、".join(sorted(current))
        if stored:
            stored_text = "、".join(sorted(stored))
            detail = f"库里已是{stored_text}，这次是{current_text}。" "要换钢厂，请先删掉原来那一条"
        else:
            detail = f"这次出现了{current_text}。请只保留一个钢厂"
        texts.append(
            f"{location} {grade}：同一个基地、同一个牌号，一个月只能有一个中标钢厂。{detail}"
        )
    return texts


_ALLOWED_WIDTHS: dict[str, frozenset[Decimal]] = {
    "冷轧": frozenset({Decimal("1250.00")}),
    "酸洗": frozenset({Decimal("1250.00")}),
    "镀锌": frozenset({Decimal("1250.00"), Decimal("1500.00")}),
}


def reject_processing_fee_over_limit(lines: list[AwardLine], *, limit: Decimal) -> None:
    """加工费大于系统设置的上限则整批拒绝。等于上限允许。"""
    ceiling = limit.quantize(Q2, rounding=ROUND_HALF_UP)
    violations: list[str] = []
    for line in lines:
        if line.processing_fee is None:
            continue
        fee = line.processing_fee.quantize(Q2, rounding=ROUND_HALF_UP)
        if fee <= ceiling:
            continue
        violations.append(
            f"{_row_prefix(line)}{line.location} {line.grade}："
            f"加工费 {fee:.2f} 元/吨，设置上限是 {ceiling:.2f} 元/吨"
        )
    if not violations:
        return
    raise BusinessException(
        "没有保存。加工费高于系统设置里的基准价加工费上限。"
        "请核对是不是把到厂价填进了加工费；上限在系统设置的「基准价」里修改。"
        + sample_text(violations)
    )


def unexpected_reference_width_warnings(lines: list[AwardLine]) -> list[str]:
    """冷轧、酸洗常见 1250；镀锌常见 1250 和 1500。其它宽度只告警，不拒绝。"""
    samples: list[str] = []
    for line in lines:
        allowed = _ALLOWED_WIDTHS.get(line.category_name)
        if allowed is None or line.width is None:
            continue
        width = line.width.quantize(Q2, rounding=ROUND_HALF_UP)
        if width in allowed:
            continue
        allowed_text = "、".join(_mm(item) for item in sorted(allowed))
        samples.append(
            f"{_row_prefix(line)}{line.location} {line.grade}："
            f"{line.category_name}参考宽度是 {_mm(width)} mm，常见是 {allowed_text} mm"
        )
    if not samples:
        return []
    return [sample_text(samples) + "。这些行已经保存。宽度不影响价格，请核对规格有没有写错。"]


def reference_width_note() -> str:
    """填写说明用。允许宽度只维护在 _ALLOWED_WIDTHS。"""
    grouped: dict[str, list[str]] = {}
    for name in ("冷轧", "酸洗", "镀锌"):
        label = "、".join(_mm(item) for item in sorted(_ALLOWED_WIDTHS[name]))
        grouped.setdefault(label, []).append(name)
    pieces = [f"{'、'.join(names)}常见 {label} mm" for label, names in grouped.items()]
    return "参考宽度：" + "，".join(pieces) + "。写成别的宽度也会保存，导入完成后会提示核对规格。"


def _mm(value: Decimal) -> str:
    text = f"{value.quantize(Q2, rounding=ROUND_HALF_UP):.2f}"
    if text.endswith(".00"):
        return text[:-3]
    return text.rstrip("0").rstrip(".")


def landed_price(base_price: Decimal, processing_fee: Decimal) -> Decimal:
    """到厂单价 + 原卷加工费，元/吨。"""
    return (base_price + processing_fee).quantize(Q2, rounding=ROUND_HALF_UP)


def reject_excessive_month_moves(
    incoming: list[AwardLine],
    previous: list[AwardLine],
    *,
    limit: Decimal,
) -> None:
    """单价加加工费相对上月超出设置范围则整批拒绝。对照键是 month_move_key。"""
    grouped: dict[tuple[str, str, Decimal, Decimal], list[AwardLine]] = defaultdict(list)
    for row in previous:
        key = month_move_key(row)
        if key is None or row.base_price is None or row.processing_fee is None:
            continue
        grouped[key].append(row)

    violations: list[str] = []
    for line in incoming:
        key = month_move_key(line)
        if key is None or line.base_price is None or line.processing_fee is None:
            continue
        counterpart = _counterpart(line, grouped.get(key, []))
        if (
            counterpart is None
            or counterpart.base_price is None
            or counterpart.processing_fee is None
        ):
            continue
        current = landed_price(line.base_price, line.processing_fee)
        prior = landed_price(counterpart.base_price, counterpart.processing_fee)
        delta = current - prior
        if abs(delta) <= limit:
            continue
        violations.append(_violation_text(line, counterpart, current, prior, delta))

    if not violations:
        return
    limit_text = f"{limit.quantize(Q2, rounding=ROUND_HALF_UP):.2f}"
    raise BusinessException(
        f"没有保存。单价加加工费和上月同基地相比，涨跌超过设置中的 ±{limit_text} 元/吨。"
        "请核对单价、加工费，或到系统设置的「基准价」里调整月度价格变动范围："
        + sample_text(violations)
    )


def _counterpart(line: AwardLine, group: list[AwardLine]) -> AwardLine | None:
    """组里已经是同一把 month_move_key。同一钢厂对那一条；只有一条时钢厂换了也对它。"""
    same_mill = [row for row in group if row.steel_mill == line.steel_mill]
    if len(same_mill) == 1:
        return same_mill[0]
    if same_mill:
        return None
    if len(group) == 1:
        return group[0]
    return None


def _violation_text(
    line: AwardLine,
    counterpart: AwardLine,
    current: Decimal,
    prior: Decimal,
    delta: Decimal,
) -> str:
    assert line.thick is not None and line.width is not None
    signed = f"{delta:+.2f}"
    thick = line.thick.quantize(Q2, rounding=ROUND_HALF_UP)
    width = line.width.quantize(Q2, rounding=ROUND_HALF_UP)
    return (
        f"{_row_prefix(line)}{line.location} {line.grade} {thick}*{width}"
        f"（{line.steel_mill}）：单价+加工费 {current:.2f}，"
        f"上月同基地 {prior:.2f}（{counterpart.steel_mill}），变动 {signed} 元/吨"
    )


def sample_text(items: list[str]) -> str:
    shown = items[:8]
    more = f"（共 {len(items)} 处，这里只列出 {len(shown)} 处）" if len(items) > len(shown) else ""
    return "；".join(shown) + more


def _row_prefix(line: AwardLine) -> str:
    if line.excel_row is None:
        return ""
    return f"第{line.excel_row}行 "
