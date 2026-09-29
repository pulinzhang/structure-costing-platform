"""
加减价政策匹配共用工具（上游能力）。

大类别名、候选筛选、base_thickness 排序、阶梯区间命中。钢厂只认 id。
供本切片（winning_thickness）与下游 costing 钢材联动共用。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from app.models.yishiyiyi import SteelPriceLadderItem, SteelPricePolicy

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


@runtime_checkable
class PolicyMatchTarget(Protocol):
    """政策匹配所需的最小行字段（costing.CalcRow 等结构满足即可）。钢厂只认 id。"""

    steel_mill_id: int | None
    category_name: str | None
    grade: str
    thickness: Decimal
    width: Decimal | None
    base_thickness: Decimal | None


@dataclass
class PolicyMatchContext:
    """轻量匹配上下文（无算价落库字段）。"""

    grade: str
    thickness: Decimal
    steel_mill_id: int | None = None
    category_name: str | None = None
    width: Decimal | None = None
    base_thickness: Decimal | None = None


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


def to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return Decimal(text)


def bound_ok(
    value: Decimal,
    bound: Decimal | None,
    operator: str | None,
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
    thickness: Decimal | None,
    width: Decimal | None,
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
    row: PolicyMatchTarget,
    policies: list[SteelPricePolicy],
) -> list[SteelPricePolicy]:
    """同年月由调用方保证。钢厂 id 相等，再按大类别名。"""
    if row.steel_mill_id is None:
        return []
    category_names = category_aliases(row.category_name or "")
    matched = [
        policy
        for policy in policies
        if policy.steel_mill_id == row.steel_mill_id
        and (policy.category_name or "").strip() in category_names
    ]
    matched.sort(key=lambda policy: policy.id or 0)
    return matched


def grade_alias_tokens(grade: str | None) -> frozenset[str]:
    """
    把政策/基价牌号拆成可互认的别名集合。

    - ``B170P1/HC180Y``：两侧都是独立牌号，互认为同一钢种
    - ``HC340/590DP``：右侧以数字开头，是双相钢屈服/抗拉写法，整段视为一个牌号
    """
    text = (grade or "").strip().replace("//", "/")
    if not text:
        return frozenset()
    parts = [part.strip() for part in text.split("/") if part.strip()]
    if len(parts) <= 1:
        return frozenset({text})
    if any(not part[0].isalpha() for part in parts):
        return frozenset({text})
    return frozenset(parts)


def grades_match(policy_grade: str | None, row_grade: str | None) -> bool:
    """牌号是否同一钢种（含斜杠双牌号别名，双向）。"""
    left = (policy_grade or "").strip()
    right = (row_grade or "").strip()
    if not left or not right:
        return False
    if left == right:
        return True
    return bool(grade_alias_tokens(left) & grade_alias_tokens(right))


def grade_exact(policy: SteelPricePolicy, row: PolicyMatchTarget) -> bool:
    grade_type = (policy.grade_type or "GRADE").strip().upper()
    if grade_type not in {"GRADE", ""}:
        return False
    return grades_match(policy.grade_value, row.grade)


def grade_generic(policy: SteelPricePolicy) -> bool:
    return not (policy.grade_value or "").strip()


def grade_category(policy: SteelPricePolicy, row: PolicyMatchTarget) -> bool:
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
    row: PolicyMatchTarget,
    prefer_base_thickness: bool,
) -> list[SteelPricePolicy]:
    def by_policy_id(policy: SteelPricePolicy) -> int:
        return policy.id or 0

    if not prefer_base_thickness:
        return sorted(policies, key=by_policy_id)

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
    exact.sort(key=by_policy_id)
    nullable.sort(key=by_policy_id)
    others.sort(key=by_policy_id)
    return exact + nullable + others


def find_best_thickness_policy(
    row: PolicyMatchTarget,
    policies: list[SteelPricePolicy],
) -> SteelPricePolicy | None:
    """
    按档案大类锁定一条 THICKNESS + CATEGORY 政策。

    钢厂 id 相等，再按大类别名。base_thickness 优先，只返回第一条。
    不按零件料厚跨政策回退（与中标厚度一览一致）。
    """
    if not (row.category_name or "").strip():
        return None
    candidates = filter_candidates(row, policies)
    thickness_policies = [
        policy
        for policy in candidates
        if policy.policy_type == "THICKNESS"
        and (policy.grade_type or "").strip().upper() == "CATEGORY"
        and grade_category(policy, row)
    ]
    if not thickness_policies:
        return None
    ordered = order_by_base_thickness(
        thickness_policies,
        row,
        prefer_base_thickness=True,
    )
    return ordered[0] if ordered else None


def match_items(
    policy: SteelPricePolicy,
    *,
    thickness: Decimal | None,
    width: Decimal | None,
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
    row: PolicyMatchTarget,
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
    row: Any,
    hit: PolicyHit,
    *,
    prefix: str,
) -> None:
    """将命中结果写回行对象（costing.CalcRow 等可变中间态）。"""
    policy, item = hit
    setattr(row, f"{prefix}_adjustment", Decimal(str(item.price_adjustment or 0)))
    setattr(row, f"{prefix}_policy_id", policy.id)
    setattr(row, f"{prefix}_ladder_item_id", item.id)
    setattr(row, f"{prefix}_excel_filename", policy.excel_filename)
    setattr(row, f"{prefix}_excel_row", item.excel_row)
    setattr(row, f"{prefix}_excel_col", item.excel_col)
