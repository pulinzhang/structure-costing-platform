"""总成核价表范围过滤（基地 / 项目 / BOM 版本）。"""

from typing import TypeVar, overload

from sqlalchemy.orm import Query, Session
from sqlalchemy.orm.query import RowReturningQuery

from app.models.costing.assembly_cost import AssemblyCost
from app.repositories.llm.location_in import location_in_clause, location_in_list_clause

_T = TypeVar("_T")
_RowT = TypeVar("_RowT", bound=tuple[object, ...])


@overload
def apply_assembly_cost_scope(
    query: RowReturningQuery[_RowT],
    db: Session,
    *,
    location: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
    locations: list[str] | None = None,
) -> RowReturningQuery[_RowT]: ...


@overload
def apply_assembly_cost_scope(
    query: Query[_T],
    db: Session,
    *,
    location: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
    locations: list[str] | None = None,
) -> Query[_T]: ...


def apply_assembly_cost_scope(
    query: Query[_T],
    db: Session,
    *,
    location: str | None,
    vehicle_model: str | None,
    bom_version: str | None,
    locations: list[str] | None = None,
) -> Query[_T]:
    if locations:
        query = query.filter(location_in_list_clause(db, AssemblyCost.location, locations))
    else:
        loc_filter = location_in_clause(db, AssemblyCost.location, location)
        if loc_filter is not None:
            query = query.filter(loc_filter)
    if vehicle_model:
        query = query.filter(AssemblyCost.vehicle_model == vehicle_model)
    if bom_version:
        query = query.filter(AssemblyCost.bom_version == bom_version)
    return query
