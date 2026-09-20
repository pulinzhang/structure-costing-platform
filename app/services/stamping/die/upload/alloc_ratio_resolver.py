"""模具布点分摊比例：共模 ×0.50，不用级进模 0.80。"""

from decimal import Decimal

from app.common.money import Q2, quantize_money

DEFAULT_ALLOC_RATIO = Decimal("1.00")
SHARED_DIE_FACTOR = Decimal("0.50")

_SHARED_DIE_KEYWORDS = ("双槽", "合并", "一出二")


def resolve_alloc_ratio(die_method: str | None, production_mode: str | None) -> Decimal:
    """扫描模具方式 + 生产方式；级进模不打折。"""
    ratio = DEFAULT_ALLOC_RATIO
    if _matches_any(die_method, production_mode, _SHARED_DIE_KEYWORDS):
        ratio *= SHARED_DIE_FACTOR
    return quantize_money(ratio, Q2)


def _matches_any(
    left: str | None,
    right: str | None,
    keywords: tuple[str, ...],
) -> bool:
    return _contains_keyword(left, keywords) or _contains_keyword(right, keywords)


def _contains_keyword(value: str | None, keywords: tuple[str, ...]) -> bool:
    if value is None:
        return False
    text = value.strip()
    if not text:
        return False
    return any(keyword in text for keyword in keywords)
