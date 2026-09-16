"""年+月闭区间生失效（对齐项目主数据，不是协议价年内 from–to）。"""

from __future__ import annotations

from app.common.timezone import now
from app.exceptions.base import BusinessException

SOP_NEW_NUMBER_REJECT = "该项目已有 SOP，不能在本页新增。换号与切点请走工程变更。"


def period(year: int, month: int) -> tuple[int, int]:
    return (year, month)


def format_period(year: int, month: int) -> str:
    return f"{year}年{month:02d}月"


def validate_period(
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
) -> None:
    if effective_month < 1 or effective_month > 12:
        raise BusinessException("生效月必须为 1–12")
    has_year = expiry_year is not None
    has_month = expiry_month is not None
    if has_year != has_month:
        raise BusinessException("失效年与失效月必须同空或同有")
    if has_month and (expiry_month is None or expiry_month < 1 or expiry_month > 12):
        raise BusinessException("失效月必须为 1–12")
    if (
        has_year
        and has_month
        and expiry_year is not None
        and expiry_month is not None
        and period(expiry_year, expiry_month) < period(effective_year, effective_month)
    ):
        raise BusinessException("失效不得早于生效")


def is_in_period(
    *,
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    as_of_year: int,
    as_of_month: int,
) -> bool:
    as_of = period(as_of_year, as_of_month)
    if as_of < period(effective_year, effective_month):
        return False
    if expiry_year is None or expiry_month is None:
        return True
    return as_of <= period(expiry_year, expiry_month)


def overlaps_year(
    *,
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
    year: int,
) -> bool:
    """与该年 1–12 月有交集（加工费年账取件，不是某月命中）。"""
    if period(effective_year, effective_month) > period(year, 12):
        return False
    if expiry_year is None or expiry_month is None:
        return True
    return period(expiry_year, expiry_month) >= period(year, 1)


def resolve_as_of_month(year: int | None, month: int | None) -> tuple[int, int]:
    """列表/树未带月用墙钟。只给一年或只给一月 → 业务拒绝。"""
    has_year = year is not None
    has_month = month is not None
    if has_year != has_month:
        raise BusinessException("年与月必须同空或同有")
    if year is None or month is None:
        clock = now()
        return clock.year, clock.month
    if month < 1 or month > 12:
        raise BusinessException("月份必须为 1–12")
    return year, month


def require_export_as_of(year: int | None, month: int | None) -> tuple[int, int]:
    """从库里按命中倒出的导出：前端必须给出年+月。"""
    if year is None or month is None:
        raise BusinessException("导出必须带年、月", code=422)
    if month < 1 or month > 12:
        raise BusinessException("月份必须为 1–12", code=422)
    return year, month
