"""钢价政策共用筛选：品类范围 / 可选键 / 导出条件。"""

from decimal import Decimal
from typing import TypeVar

from sqlalchemy import distinct
from sqlalchemy.orm import InstrumentedAttribute, Query, Session

from app.models.yishiyiyi import SteelPricePolicy

TValue = TypeVar("TValue")
_T = TypeVar("_T")


def apply_category_scope(
    query: Query[_T],
    *,
    category_names_in: frozenset[str] | None = None,
    category_filter_no_match: bool = False,
) -> Query[_T]:
    if category_filter_no_match:
        return query.filter(SteelPricePolicy.id < 0)
    if category_names_in is not None:
        return query.filter(SteelPricePolicy.category_name.in_(category_names_in))
    return query


def apply_optional_policy_filters(
    query: Query[_T],
    *,
    grade_type: str | None = None,
    grade_value: str | None = None,
    base_thickness: Decimal | None = None,
) -> Query[_T]:
    """对 policy 的可选过滤字段应用条件（支持 NULL 精确匹配）。"""
    if grade_type is not None:
        query = query.filter(SteelPricePolicy.grade_type == grade_type)
    else:
        query = query.filter(SteelPricePolicy.grade_type.is_(None))

    if grade_value is not None:
        query = query.filter(SteelPricePolicy.grade_value == grade_value)
    else:
        query = query.filter(SteelPricePolicy.grade_value.is_(None))

    if base_thickness is not None:
        query = query.filter(SteelPricePolicy.base_thickness == base_thickness)
    else:
        query = query.filter(SteelPricePolicy.base_thickness.is_(None))

    return query


def apply_export_filters(
    query: Query[_T],
    *,
    year: int | None = None,
    month: int | None = None,
    steel_mill: str | None = None,
    steel_mill_id: int | None = None,
    category_names_in: frozenset[str] | None = None,
    category_filter_no_match: bool = False,
    policy_type: str | None = None,
) -> Query[_T]:
    """导出查询共用的政策筛选条件。"""
    if year is not None:
        query = query.filter(SteelPricePolicy.year == year)
    if month is not None:
        query = query.filter(SteelPricePolicy.month == month)
    if steel_mill_id is not None:
        query = query.filter(SteelPricePolicy.steel_mill_id == steel_mill_id)
    elif steel_mill:
        query = query.filter(SteelPricePolicy.steel_mill == steel_mill)
    query = apply_category_scope(
        query,
        category_names_in=category_names_in,
        category_filter_no_match=category_filter_no_match,
    )
    if policy_type:
        query = query.filter(SteelPricePolicy.policy_type == policy_type)
    return query


def distinct_values(
    db: Session,
    column: InstrumentedAttribute[TValue],
    *,
    filter_none: bool = False,
    descending: bool = False,
) -> list[TValue]:
    """通用 distinct 值查询。"""
    query = db.query(distinct(column))
    if filter_none:
        query = query.filter(column.isnot(None))
    order_col = column.desc() if descending else column.asc()
    return [r[0] for r in query.order_by(order_col).all()]
