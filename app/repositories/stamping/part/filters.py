"""列表共用筛选：工厂单值 vs 多值。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy import false
from sqlalchemy.orm import InstrumentedAttribute, Query

from app.models.stamping import StampingPart

_T = TypeVar("_T")
_StringColumn = InstrumentedAttribute[str] | InstrumentedAttribute[str | None]

_PART_LIST_ORDER = (
    StampingPart.location,
    StampingPart.vehicle_model,
    StampingPart.version,
    StampingPart.stamping_supplier,
    StampingPart.id,
)


def _filter_supplier(
    q: Query[_T],
    column: _StringColumn,
    stamping_supplier: str | None,
    stamping_suppliers: Sequence[str] | None,
) -> Query[_T]:
    if stamping_suppliers is not None:
        if not stamping_suppliers:
            return q.filter(false())
        return q.filter(column.in_(stamping_suppliers))
    if stamping_supplier is not None:
        return q.filter(column == stamping_supplier)
    return q
