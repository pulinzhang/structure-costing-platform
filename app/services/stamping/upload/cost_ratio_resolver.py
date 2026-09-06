"""
新增工序的默认 cost_ratio。Excel 无此列；已有工序沿用库中值。

规则只写在 docs/stamping/stamping-process-confirmation-design.md §4。
"""

import re
from decimal import Decimal
from typing import Any

from app.common.money import Q2, quantize_money

DEFAULT_COST_RATIO = Decimal("1.00")
SHARED_DIE_FACTOR = Decimal("0.50")
PROGRESSIVE_DIE_FACTOR = Decimal("0.80")

_SHARED_DIE_KEYWORDS = ("双槽", "合并", "一出二")
_FULL_SHARED_KEYWORDS = ("双槽", "合并")
_ONE_OUT_OF_TWO_KEYWORDS = ("一出二",)
_SHARED_FIRST_KEYWORDS = ("共用",)
_MATE_PROCESS_CODE_KEYWORDS = ("双槽", "合并", "共用")
_PROGRESSIVE_DIE_KEYWORDS = ("级进模",)
_PROCESS_CODE_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def resolve_cost_ratio(
    automation: Any,
    process_method: Any,
    process_code: Any = None,
    previous_automation: Any = None,
) -> Decimal:
    """零件级叠乘（右件继承上一件级进见设计 §4）。"""
    ratio = DEFAULT_COST_RATIO
    is_shared = _matches_any(automation, process_method, _SHARED_DIE_KEYWORDS) or _contains_keyword(
        process_code, _SHARED_DIE_KEYWORDS
    )
    is_progressive = _is_progressive_text(automation) or _is_progressive_text(process_method)
    if (
        is_shared
        and _is_progressive_text(previous_automation)
        and _contains_keyword(process_code, _MATE_PROCESS_CODE_KEYWORDS)
    ):
        is_progressive = True
    if is_shared:
        ratio *= SHARED_DIE_FACTOR
    if is_progressive:
        ratio *= PROGRESSIVE_DIE_FACTOR
    return quantize_money(ratio, Q2)


def is_prg_process_code(process_code: Any) -> bool:
    """工序代码切词含 PRG。"""
    tokens = {token.upper() for token in _PROCESS_CODE_TOKEN_RE.findall(str(process_code or ""))}
    return "PRG" in tokens


def is_shared_first_process_code(process_code: Any) -> bool:
    """第一序代码含「共用」。"""
    return _contains_keyword(process_code, _SHARED_FIRST_KEYWORDS)


def later_ops_have_shared_die(process_codes: list[Any]) -> bool:
    """第一序之后的工序代码是否含双槽/合并。"""
    return any(_contains_keyword(code, _FULL_SHARED_KEYWORDS) for code in process_codes)


def later_ops_are_blank(process_codes: list[Any]) -> bool:
    """后续序有行但代码全空：右件后序与左件共用。"""
    if not process_codes:
        return False
    return all(not str(code or "").strip() for code in process_codes)


def is_prg_family(
    first_process_code: Any,
    previous_first_process_code: Any = None,
) -> bool:
    if is_prg_process_code(first_process_code):
        return True
    return is_prg_process_code(previous_first_process_code) and _contains_keyword(
        first_process_code, _SHARED_FIRST_KEYWORDS
    )


def resolve_new_process_cost_ratio(
    *,
    automation: Any,
    process_method: Any,
    process_code: Any,
    is_first_process: bool,
    process_count: int,
    first_process_code: Any,
    previous_automation: Any = None,
    previous_first_process_code: Any = None,
    later_ops_are_shared: bool = False,
) -> Decimal:
    """新增默认比例。多序 PRG / 一出二条料见设计 §4，其余走 resolve_cost_ratio。"""
    if process_count > 1 and is_prg_family(first_process_code, previous_first_process_code):
        if is_first_process:
            return quantize_money(PROGRESSIVE_DIE_FACTOR, Q2)
        if _later_ops_share_die(
            process_code, process_method, later_ops_are_shared=later_ops_are_shared
        ):
            return quantize_money(SHARED_DIE_FACTOR, Q2)
        return DEFAULT_COST_RATIO
    if process_count > 1 and _contains_keyword(process_method, _ONE_OUT_OF_TWO_KEYWORDS):
        if is_first_process:
            return resolve_cost_ratio(
                automation,
                process_method,
                process_code=process_code,
                previous_automation=previous_automation,
            )
        if _later_ops_share_die(
            process_code, process_method, later_ops_are_shared=later_ops_are_shared
        ):
            return quantize_money(SHARED_DIE_FACTOR, Q2)
        return DEFAULT_COST_RATIO
    return resolve_cost_ratio(
        automation,
        process_method,
        process_code=process_code,
        previous_automation=previous_automation,
    )


def _later_ops_share_die(
    process_code: Any,
    process_method: Any,
    *,
    later_ops_are_shared: bool,
) -> bool:
    """后序共模：双槽/合并，或成对邻件后序空码/双槽。一出二本身不表示后序共模。"""
    if later_ops_are_shared:
        return True
    if _contains_keyword(process_code, _FULL_SHARED_KEYWORDS):
        return True
    return _contains_keyword(process_method, _FULL_SHARED_KEYWORDS)


def _is_progressive_text(value: Any) -> bool:
    """含「级进模」，或单元格整格为「级进」。不把「级进落料」当级进模。"""
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    if any(keyword in text for keyword in _PROGRESSIVE_DIE_KEYWORDS):
        return True
    return text == "级进"


def _matches_any(automation: Any, process_method: Any, keywords: tuple[str, ...]) -> bool:
    return _contains_keyword(process_method, keywords) or _contains_keyword(automation, keywords)


def _contains_keyword(value: Any, keywords: tuple[str, ...]) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text:
        return False
    return any(keyword in text for keyword in keywords)
