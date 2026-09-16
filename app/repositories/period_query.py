"""列表按月命中：闭区间 SQL（effective <= as_of 且 expiry 空或 as_of <= expiry）。"""

from __future__ import annotations

from sqlalchemy import ColumnElement, and_, or_
from sqlalchemy.orm import InstrumentedAttribute


def period_hit_clause(
    effective_year: InstrumentedAttribute[int],
    effective_month: InstrumentedAttribute[int],
    expiry_year: InstrumentedAttribute[int | None],
    expiry_month: InstrumentedAttribute[int | None],
    as_of_year: int,
    as_of_month: int,
) -> ColumnElement[bool]:
    started = or_(
        effective_year < as_of_year,
        and_(effective_year == as_of_year, effective_month <= as_of_month),
    )
    not_ended = or_(
        expiry_year.is_(None),
        expiry_year > as_of_year,
        and_(expiry_year == as_of_year, expiry_month >= as_of_month),
    )
    return and_(started, not_ended)


def period_overlaps_year_clause(
    effective_year: InstrumentedAttribute[int],
    expiry_year: InstrumentedAttribute[int | None],
    year: int,
) -> ColumnElement[bool]:
    """与该年有交集：生效年 ≤ 该年，且失效空或失效年 ≥ 该年。"""
    return and_(
        effective_year <= year,
        or_(expiry_year.is_(None), expiry_year >= year),
    )
