"""加减价匹配共用工具（已归属上游 yishiyiyi.policy.match）。

保留本模块路径仅为兼容旧 import；新代码请直接从
`app.services.yishiyiyi.policy.match.adjustment_common` 引入。
"""

from app.services.yishiyiyi.policy.match.adjustment_common import (
    PolicyHit,
    PolicyMatchContext,
    PolicyMatchTarget,
    apply_hit,
    bound_ok,
    category_aliases,
    filter_candidates,
    find_best_hit,
    grade_category,
    grade_exact,
    grade_generic,
    item_matches_dims,
    match_items,
    normalize_steel_mill,
    order_by_base_thickness,
    steel_mill_aliases,
    steel_mill_match_rank,
    steel_mill_matches,
    to_decimal,
)

__all__ = [
    "PolicyHit",
    "PolicyMatchContext",
    "PolicyMatchTarget",
    "apply_hit",
    "bound_ok",
    "category_aliases",
    "filter_candidates",
    "find_best_hit",
    "grade_category",
    "grade_exact",
    "grade_generic",
    "item_matches_dims",
    "match_items",
    "normalize_steel_mill",
    "order_by_base_thickness",
    "steel_mill_aliases",
    "steel_mill_match_rank",
    "steel_mill_matches",
    "to_decimal",
]
