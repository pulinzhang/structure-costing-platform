"""
加减价政策匹配共用工具（上游能力）。

钢厂/大类别名、候选筛选、base_thickness 排序、阶梯区间命中。
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

# 基价钢厂（极简）↔ 政策钢厂（简称 / 带(新) / 集团名）
# 「X」与「X(新)」由 steel_mill_aliases 自动互通，不必逐家手写。
# 此处只维护跨品牌/集团等非常规别名。
_STEEL_MILL_ALIASES: dict[str, frozenset[str]] = {
    "本钢": frozenset({"本钢", "鞍钢集团"}),
    "鞍钢集团": frozenset({"本钢", "鞍钢集团"}),
    "马钢": frozenset({"马钢", "马钢(新)"}),
    "马钢(新)": frozenset({"马钢", "马钢(新)"}),
    "山钢": frozenset({"山钢", "山钢(新)"}),
    "山钢(新)": frozenset({"山钢", "山钢(新)"}),
    "唐钢": frozenset({"唐钢", "唐钢(新)"}),
    "唐钢(新)": frozenset({"唐钢", "唐钢(新)"}),
}

PolicyHit = tuple[SteelPricePolicy, SteelPriceLadderItem]


@runtime_checkable
class PolicyMatchTarget(Protocol):
    """政策匹配所需的最小行字段（costing.CalcRow 等结构满足即可）。"""

    steel_mill: str | None
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
    steel_mill: str | None = None
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


def normalize_steel_mill(steel_mill: str | None) -> str:
    """钢厂名称归一化：去空白、全角括号→半角。"""
    name = (steel_mill or "").strip()
    if not name:
        return ""
    return name.replace("（", "(").replace("）", ")")


def _steel_mill_lookup_key(name: str) -> str:
    """别名表查找键：ASCII 名忽略大小写（VAMA / vama）。"""
    if name.isascii():
        return name.casefold()
    return name


def steel_mill_aliases(steel_mill: str | None) -> frozenset[str]:
    """
    返回与基价钢厂可互通的政策钢厂名集合（均已归一化）。

    匹配优先级由 steel_mill_match_rank 决定，本函数只负责「能不能配上」。
    除显式别名表外，任意钢厂名自动与其「(新)」变体双向互通
    （基价写「唐钢」、政策写「唐钢(新)」可命中）。
    """
    name = normalize_steel_mill(steel_mill)
    if not name:
        return frozenset()

    aliases = _STEEL_MILL_ALIASES.get(name)
    if aliases is None:
        key = _steel_mill_lookup_key(name)
        for raw, values in _STEEL_MILL_ALIASES.items():
            if _steel_mill_lookup_key(raw) == key:
                aliases = values
                break

    base: set[str] = {normalize_steel_mill(item) for item in aliases} if aliases else {name}
    return frozenset(_expand_new_variant_mills(base))


_NEW_SUFFIX = "(新)"


def _expand_new_variant_mills(names: set[str]) -> set[str]:
    """为集合内每个名称补上 / 去掉「(新)」对偶名。"""
    expanded = set(names)
    for item in names:
        if item.endswith(_NEW_SUFFIX):
            root = item[: -len(_NEW_SUFFIX)].strip()
            if root:
                expanded.add(root)
        else:
            expanded.add(f"{item}{_NEW_SUFFIX}")
    return expanded


def _steel_mills_equal(left: str, right: str) -> bool:
    if left == right:
        return True
    if left.isascii() and right.isascii():
        return left.casefold() == right.casefold()
    return False


def steel_mill_matches(row_mill: str | None, policy_mill: str | None) -> bool:
    """判断基价钢厂与政策钢厂是否同一主体（含别名）。"""
    policy_name = normalize_steel_mill(policy_mill)
    if not policy_name:
        return False
    aliases = steel_mill_aliases(row_mill)
    if not aliases:
        return False
    if policy_name in aliases:
        return True
    return any(_steel_mills_equal(policy_name, alias) for alias in aliases)


def steel_mill_match_rank(row_mill: str | None, policy_mill: str | None) -> int:
    """
    钢厂命中优先级（数值越小越优先）。

    0 = 归一化后精确相等
    1 = 普通别名（如 本钢 ↔ 鞍钢集团）
    2 = 基价为普通名、政策为「(新)」变体（如 马钢 → 马钢(新)）
    """
    row_name = normalize_steel_mill(row_mill)
    policy_name = normalize_steel_mill(policy_mill)
    if not row_name or not policy_name:
        return 99
    if _steel_mills_equal(row_name, policy_name):
        return 0
    if policy_name.endswith("(新)") and not row_name.endswith("(新)"):
        return 2
    return 1


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
    """
    按钢厂别名 + 大类别名筛选候选政策。

    结果按钢厂命中优先级排序：精确名 > 普通别名 > (新) 变体，
    以便后续厚度/宽度匹配优先落在更贴近基价的政策上。
    """
    category_names = category_aliases(row.category_name or "")
    matched = [
        p
        for p in policies
        if steel_mill_matches(row.steel_mill, p.steel_mill)
        and (p.category_name or "").strip() in category_names
    ]
    matched.sort(
        key=lambda p: (
            steel_mill_match_rank(row.steel_mill, p.steel_mill),
            normalize_steel_mill(p.steel_mill),
            p.id or 0,
        )
    )
    return matched


def grade_exact(policy: SteelPricePolicy, row: PolicyMatchTarget) -> bool:
    grade_value = (policy.grade_value or "").strip()
    if not grade_value:
        return False
    if grade_value != (row.grade or "").strip():
        return False
    grade_type = (policy.grade_type or "GRADE").strip().upper()
    return grade_type in {"GRADE", ""}


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
    def mill_key(policy: SteelPricePolicy) -> tuple[Any, ...]:
        return (
            steel_mill_match_rank(row.steel_mill, policy.steel_mill),
            normalize_steel_mill(policy.steel_mill),
            policy.id or 0,
        )

    if not prefer_base_thickness:
        return sorted(policies, key=mill_key)

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
    exact.sort(key=mill_key)
    nullable.sort(key=mill_key)
    others.sort(key=mill_key)
    return exact + nullable + others


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
