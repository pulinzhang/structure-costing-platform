"""查询窗口：闭区间自然月展开。"""

from __future__ import annotations

from app.exceptions.base import BusinessException

MAX_WINDOW_MONTHS = 12


def expand_months(
    *,
    start_year: int,
    start_month: int,
    end_year: int,
    end_month: int,
) -> list[tuple[int, int]]:
    start_index = start_year * 12 + start_month
    end_index = end_year * 12 + end_month
    if start_index > end_index:
        raise BusinessException("开始年月不得晚于结束年月")
    count = end_index - start_index + 1
    if count > MAX_WINDOW_MONTHS:
        raise BusinessException(f"查询窗口最多 {MAX_WINDOW_MONTHS} 个月，当前 {count} 个月")
    months: list[tuple[int, int]] = []
    for offset in range(count):
        year, remainder = divmod(start_index + offset - 1, 12)
        months.append((year, remainder + 1))
    return months


def month_header(year: int, month: int) -> str:
    return f"{year % 100}年{month}月 结算价格（元）"
