"""加减价政策生效期：期货口径（括号内为冲焊件原料实际生效年月）。"""

from __future__ import annotations

import re
from dataclasses import dataclass

_PAREN_PERIOD_RE = re.compile(r"[（(]\s*(\d{4})\s*年\s*(\d{1,2})\s*月")


@dataclass(frozen=True)
class PolicyEffectivePeriod:
    """政策生效年月（入库 year / month）。"""

    year: int
    month: int


def effective_period_from_policy_filename(filename: str) -> PolicyEffectivePeriod | None:
    """
    从文件名括号段解析生效年月。

    例：外协钢板2026年1月订单（2026年2月 冲焊件原料）一事一议价格厚度加减价.xlsx
    → year=2026, month=2（期货：订 1 月、原料 2 月生效）
    """
    match = _PAREN_PERIOD_RE.search(filename or "")
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        return None
    return PolicyEffectivePeriod(year=year, month=month)
