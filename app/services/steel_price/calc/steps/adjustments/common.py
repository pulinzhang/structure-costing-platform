"""加减价匹配共用工具。"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from app.models.steel_price_policy import SteelPriceLadderItem, SteelPricePolicy
from app.services.steel_price.calc.models import CalcRow

# 基价大类（冷轧/镀锌/酸洗）↔ 政策大类（冷轧钢/镀锌钢/酸洗钢）
_CATEGORY_ALIASES: dict[str, frozenset[str]] = {
    "冷轧": frozenset({"冷轧", "冷轧钢"}),
    "冷轧钢": frozenset({"冷轧", "冷轧钢"}),
    "镀锌": frozenset({"镀锌", "镀锌钢"}),
    "镀锌钢": frozenset({"镀锌", "镀锌钢"}),
    "酸洗": frozenset({"酸洗", "酸洗钢"}),
    "酸洗钢": frozenset({"酸洗", "酸洗钢"}),
}

PolicyHit = tuple[SteelPricePolicy, SteelPriceLadderItem]


def category_aliases(category_name: str) -> frozenset[str]:
    name = (category_name or "").strip()
    if not name:
        return frozenset()
    aliases = _CATEGORY_ALIASES.get(name)
    if aliases:
        return aliases
    if name.endswith("钢") and len(name) > 1:
        return frozenset({name, name[:-1]})
    return frozenset({name, f"{name}钢"})


def to_decimal(value) -> Optional[Decimal]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return Decimal(text)


def bound_ok(
    value: Decimal,
    bound: Optional[Decimal],
    operator: Optional[str],
    *,
    default_op: str,
) -> bool:
    """
    区间边界判断（对照 THICKNESS 阶梯真实数据）。

    常见形态：
    - [min, max)  → min_op='>=', max_op='<'   例：0.5>= … 0.8<
    - (min, max]  → min_op='>',  max_op='<='  例：0> … 0.5<=
    - (min, max)  → min_op='>',  max_op='<'   例：3.5> … 5<
    - [min, +∞)  → max 为空，只判 min        例：2.5>= / 5>
    - bound 为 None / 空：该侧不做判断

    比较方向始终是 value 相对 bound：
    min=1 min_op='>=' → value >= 1
    max=0.8 max_op='<' → value < 0.8
    """
    if bound is None:
        return True
    op = (operator or default_op).strip()
    if op == ">=":
        return value >= bound
    if op == ">":
        return value > bound
    if op == "<=":
        return value <= bound
    if op == "<":
        return value < bound
    return True


def item_matches_dims(
    item: SteelPriceLadderItem,
    *,
    thickness: Optional[Decimal],
    width: Optional[Decimal],
    check_thickness: bool,
    check_width: bool,
) -> bool:
    if check_thickness:
        if thickness is None:
            return False
        if not bound_ok(
            thickness,
            to_decimal(item.thick_min),
            item.thick_min_operator,
            default_op=">=",
        ):
            return False
        if not bound_ok(
            thickness,
            to_decimal(item.thick_max),
            item.thick_max_operator,
            default_op="<",
        ):
            return False

    if check_width:
        if width is None:
            return False
        if not bound_ok(
            width,
            to_decimal(item.width_min),
            item.width_min_operator,
            default_op=">=",
        ):
            return False
        if not bound_ok(
            width,
            to_decimal(item.width_max),
            item.width_max_operator,
            default_op="<",
        ):
            return False

    return True


def filter_candidates(
    row: CalcRow,
    policies: list[SteelPricePolicy],
) -> list[SteelPricePolicy]:
    mill = (row.steel_mill or "").strip()
    aliases = category_aliases(row.category_name or "")
    return [
        p
        for p in policies
        if (p.steel_mill or "").strip() == mill
        and (p.category_name or "").strip() in aliases
    ]


def grade_exact(policy: SteelPricePolicy, row: CalcRow) -> bool:
    grade_value = (policy.grade_value or "").strip()
    if not grade_value:
        return False
    if grade_value != (row.grade or "").strip():
        return False
    grade_type = (policy.grade_type or "GRADE").strip().upper()
    return grade_type in {"GRADE", ""}


def grade_generic(policy: SteelPricePolicy) -> bool:
    return not (policy.grade_value or "").strip()


def grade_category(policy: SteelPricePolicy, row: CalcRow) -> bool:
    grade_type = (policy.grade_type or "").strip().upper()
    if grade_type != "CATEGORY":
        return False
    grade_value = (policy.grade_value or "").strip()
    if not grade_value:
        return False
    aliases = category_aliases(row.category_name or "")
    return grade_value in aliases or grade_value == (row.category_name or "").strip()


def order_by_base_thickness(
    policies: list[SteelPricePolicy],
    row: CalcRow,
    prefer_base_thickness: bool,
) -> list[SteelPricePolicy]:
    if not prefer_base_thickness:
        return policies

    row_base = row.base_thickness
    exact: list[SteelPricePolicy] = []
    nullable: list[SteelPricePolicy] = []
    others: list[SteelPricePolicy] = []
    for policy in policies:
        policy_base = to_decimal(policy.base_thickness)
        if row_base is not None and policy_base is not None and policy_base == row_base:
            exact.append(policy)
        elif policy_base is None:
            nullable.append(policy)
        else:
            others.append(policy)
    return exact + nullable + others


def match_items(
    policy: SteelPricePolicy,
    *,
    thickness: Optional[Decimal],
    width: Optional[Decimal],
    check_thickness: bool,
    check_width: bool,
) -> SteelPriceLadderItem | None:
    hits: list[SteelPriceLadderItem] = []
    for item in policy.items or []:
        if item_matches_dims(
            item,
            thickness=thickness,
            width=width,
            check_thickness=check_thickness,
            check_width=check_width,
        ):
            hits.append(item)
    if not hits:
        return None
    hits.sort(key=lambda x: (x.sort_order or 0, x.id or 0))
    return hits[0]


def find_best_hit(
    row: CalcRow,
    candidates: list[SteelPricePolicy],
    *,
    policy_types: tuple[str, ...],
    check_thickness: bool,
    check_width: bool,
    prefer_base_thickness: bool,
) -> PolicyHit | None:
    typed = [p for p in candidates if p.policy_type in policy_types]
    if not typed:
        return None

    ranked_groups = [
        [p for p in typed if grade_exact(p, row)],
        [p for p in typed if grade_generic(p)],
        [p for p in typed if grade_category(p, row)],
    ]

    for group in ranked_groups:
        if not group:
            continue
        ordered = order_by_base_thickness(group, row, prefer_base_thickness)
        for policy in ordered:
            hit = match_items(
                policy,
                thickness=row.thickness,
                width=row.width,
                check_thickness=check_thickness,
                check_width=check_width,
            )
            if hit is not None:
                return policy, hit
    return None


def apply_hit(
    row: CalcRow,
    hit: PolicyHit,
    *,
    prefix: str,
) -> None:
    policy, item = hit
    setattr(row, f"{prefix}_adjustment", Decimal(str(item.price_adjustment or 0)))
    setattr(row, f"{prefix}_policy_id", policy.id)
    setattr(row, f"{prefix}_ladder_item_id", item.id)
    setattr(row, f"{prefix}_excel_filename", policy.excel_filename)
    setattr(row, f"{prefix}_excel_row", item.excel_row)
    setattr(row, f"{prefix}_excel_col", item.excel_col)
