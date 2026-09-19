"""加减价 / 基准价样例生效期：期货口径。

优先级：父目录名（如 ``25年9月订单10月冲焊件``）> 文件名括号内原料年月。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_PAREN_SEGMENT_RE = re.compile(r"[（(]([^）)]+)[）)]")
# 例：2026年2月 / 24年7月 / 2025年6月和7月
_PERIOD_IN_PAREN_RE = re.compile(r"(\d{2,4})\s*年\s*(\d{1,2})\s*月(?:\s*和\s*(\d{1,2})\s*月)?")
# 跨年：25年12月订26年1月冲焊件
_DIR_CROSS_YEAR_RE = re.compile(
    r"(\d{2,4})\s*年\s*(\d{1,2})\s*月?\s*订(?:单)?\s*(\d{2,4})\s*年\s*(\d{1,2})\s*月"
)
# 同年：25年9月订单10月 / 26年1月订2月 / 24年11月订12月
_DIR_SAME_YEAR_RE = re.compile(r"(\d{2,4})\s*年\s*(\d{1,2})\s*月?\s*订(?:单)?\s*(\d{1,2})\s*月")


@dataclass(frozen=True)
class PolicyEffectivePeriod:
    """政策 / 基价生效年月（入库 year / month）。"""

    year: int
    month: int


def _normalize_year(raw_year: int) -> int:
    if raw_year < 100:
        return 2000 + raw_year
    return raw_year


def _period_or_none(year: int, month: int) -> PolicyEffectivePeriod | None:
    if month < 1 or month > 12:
        return None
    return PolicyEffectivePeriod(year=year, month=month)


def effective_periods_from_directory_name(directory_name: str) -> list[PolicyEffectivePeriod]:
    """
    从订单目录名解析原料生效月。

    例：
    - ``25年9月订单10月冲焊件及废料价格`` → [2025-10]
    - ``25年12月订26年1月冲焊件及废料价格`` → [2026-01]
    - ``26年1月订2月冲焊件及废料价格`` → [2026-02]
    """
    name = directory_name or ""
    cross = _DIR_CROSS_YEAR_RE.search(name)
    if cross:
        period = _period_or_none(
            _normalize_year(int(cross.group(3))),
            int(cross.group(4)),
        )
        return [period] if period is not None else []

    same = _DIR_SAME_YEAR_RE.search(name)
    if same:
        period = _period_or_none(
            _normalize_year(int(same.group(1))),
            int(same.group(3)),
        )
        return [period] if period is not None else []
    return []


def effective_periods_from_policy_filename(filename: str) -> list[PolicyEffectivePeriod]:
    """
    从文件名括号段解析全部生效年月。

    例：
    - …（2026年2月 冲焊件原料）… → [2026-02]
    - …（2025年6月和7月冲焊件原料）… → [2025-06, 2025-07]
    - …（24年7月原料）… → [2024-07]
    """
    paren_match = _PAREN_SEGMENT_RE.search(filename or "")
    if not paren_match:
        return []
    period_match = _PERIOD_IN_PAREN_RE.search(paren_match.group(1))
    if not period_match:
        return []

    year = _normalize_year(int(period_match.group(1)))
    first_month = int(period_match.group(2))
    periods: list[PolicyEffectivePeriod] = []
    first = _period_or_none(year, first_month)
    if first is not None:
        periods.append(first)

    second_raw = period_match.group(3)
    if second_raw is not None:
        second = _period_or_none(year, int(second_raw))
        if second is not None and second not in periods:
            periods.append(second)
    return periods


def effective_period_from_policy_filename(filename: str) -> PolicyEffectivePeriod | None:
    """
    从文件名括号段解析首个生效年月（兼容单月文件名）。

    例：外协钢板2026年1月订单（2026年2月 冲焊件原料）一事一议价格厚度加减价.xlsx
    → year=2026, month=2（期货：订 1 月、原料 2 月生效）
    """
    periods = effective_periods_from_policy_filename(filename)
    return periods[0] if periods else None


def effective_periods_from_sample_path(
    path: Path,
    *,
    root: Path | None = None,
) -> list[PolicyEffectivePeriod]:
    """
    样例路径解析生效期：目录名优先，其次文件名括号。

    ``25年9月订单10月…/…（25年9月原料）….xlsx`` → [2025-10]（跟目录，不跟错文件名）。
    """
    resolved = path.resolve()
    root_resolved = root.resolve() if root is not None else None
    for parent in resolved.parents:
        if root_resolved is not None:
            try:
                parent.relative_to(root_resolved)
            except ValueError:
                break
        periods = effective_periods_from_directory_name(parent.name)
        if periods:
            return periods
    return effective_periods_from_policy_filename(resolved.name)
