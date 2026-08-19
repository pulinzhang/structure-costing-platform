"""
新增工序的默认费用比例。

Excel 没有 cost_ratio 列。仅当工序是本次新写入（库中没有同零件号+工序号）时，
按零件的「自动化」「工艺方法」叠乘默认比例：

- 双槽 / 合并（共模同冲）→ ×0.50
- 级进模（全自动，更便宜）→ ×0.80
- 两者同时 → 0.40

已有工序沿用库中值，不走本规则。
"""

from decimal import Decimal
from typing import Any

from app.common.money import Q2, quantize_money

DEFAULT_COST_RATIO = Decimal("1.00")
SHARED_DIE_FACTOR = Decimal("0.50")
PROGRESSIVE_DIE_FACTOR = Decimal("0.80")

_SHARED_DIE_KEYWORDS = ("双槽", "合并")
_PROGRESSIVE_DIE_KEYWORDS = ("级进模",)


def resolve_cost_ratio(automation: Any, process_method: Any) -> Decimal:
    """
    根据自动化、工艺方法返回新增工序的单次冲压费用比例。

    双槽/合并与级进模独立判定、同时叠乘。
    """
    ratio = DEFAULT_COST_RATIO
    if _matches_any(automation, process_method, _SHARED_DIE_KEYWORDS):
        ratio *= SHARED_DIE_FACTOR
    if _matches_any(automation, process_method, _PROGRESSIVE_DIE_KEYWORDS):
        ratio *= PROGRESSIVE_DIE_FACTOR
    return quantize_money(ratio, Q2)


def _matches_any(automation: Any, process_method: Any, keywords: tuple[str, ...]) -> bool:
    return _contains_keyword(process_method, keywords) or _contains_keyword(
        automation, keywords
    )


def _contains_keyword(value: Any, keywords: tuple[str, ...]) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    return any(keyword in text for keyword in keywords)
