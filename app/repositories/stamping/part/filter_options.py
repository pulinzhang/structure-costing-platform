"""冲压零件筛选下拉与级联选项。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from sqlalchemy.orm import Query, Session

from app.common.types.repository_types import StampingPartCascadeFilterOptions
from app.models.stamping import StampingPart
from app.repositories.period_query import period_hit_clause, period_overlaps_year_clause
from app.repositories.stamping.part.filters import _StringColumn
from app.repositories.stamping.part.types import StampingPartFilterOptionValues

_T = TypeVar("_T")


class StampingPartFilterOptions:
    def get_filter_options(self, db: Session) -> StampingPartFilterOptionValues:
        """
        获取筛选下拉框的可选值。
        返回键名与 StampingPartListFilterOptions VO 对齐。
        """
        locations = (
            db.query(StampingPart.location)
            .distinct()
            .filter(StampingPart.location.isnot(None), StampingPart.location != "")
            .order_by(StampingPart.location)
            .all()
        )
        stamping_suppliers = (
            db.query(StampingPart.stamping_supplier)
            .distinct()
            .filter(
                StampingPart.stamping_supplier.isnot(None), StampingPart.stamping_supplier != ""
            )
            .order_by(StampingPart.stamping_supplier)
            .all()
        )
        vehicle_models = (
            db.query(StampingPart.vehicle_model)
            .distinct()
            .filter(StampingPart.vehicle_model.isnot(None), StampingPart.vehicle_model != "")
            .order_by(StampingPart.vehicle_model)
            .all()
        )
        versions = (
            db.query(StampingPart.version)
            .distinct()
            .filter(StampingPart.version.isnot(None), StampingPart.version != "")
            .order_by(StampingPart.version)
            .all()
        )
        materials = (
            db.query(StampingPart.material)
            .distinct()
            .filter(StampingPart.material.isnot(None), StampingPart.material != "")
            .order_by(StampingPart.material)
            .all()
        )
        return {
            "locations": [r[0] for r in locations],
            "stamping_suppliers": [r[0] for r in stamping_suppliers],
            "vehicle_models": [r[0] for r in vehicle_models],
            "versions": [r[0] for r in versions],
            "materials": [r[0] for r in materials],
        }

    def get_cascade_filter_options(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        overlap_year: int | None = None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
    ) -> StampingPartCascadeFilterOptions:
        """
        级联筛选选项（未选维度不参与过滤，厂优先与车优先均可）：
        - 基地：全量（Service 用 list_registered 覆盖）
        - 配套车型：按已选基地、冲压工厂过滤
        - 版本：按已选基地、冲压工厂、车型过滤
        - 冲压工厂：按已选基地、车型、版本过滤
        """
        registered_locations = self._distinct_string_values(db, StampingPart.location)

        vehicle_q = self._scope_cascade_query(
            db.query(StampingPart.vehicle_model).distinct(),
            locations=locations,
            location=location,
            overlap_year=overlap_year,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )
        if stamping_supplier:
            vehicle_q = vehicle_q.filter(StampingPart.stamping_supplier == stamping_supplier)
        vehicle_models = self._collect_distinct_strings(vehicle_q, StampingPart.vehicle_model)

        version_q = self._scope_cascade_query(
            db.query(StampingPart.version).distinct(),
            locations=locations,
            location=location,
            overlap_year=overlap_year,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )
        if stamping_supplier:
            version_q = version_q.filter(StampingPart.stamping_supplier == stamping_supplier)
        if vehicle_model:
            version_q = version_q.filter(StampingPart.vehicle_model == vehicle_model)
        versions = self._collect_distinct_strings(version_q, StampingPart.version)

        supplier_q = self._scope_cascade_query(
            db.query(StampingPart.stamping_supplier).distinct(),
            locations=locations,
            location=location,
            overlap_year=overlap_year,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        )
        if vehicle_model:
            supplier_q = supplier_q.filter(StampingPart.vehicle_model == vehicle_model)
        if version:
            supplier_q = supplier_q.filter(StampingPart.version == version)
        stamping_suppliers = self._collect_distinct_strings(
            supplier_q, StampingPart.stamping_supplier
        )

        return {
            "locations": registered_locations,
            "stamping_suppliers": stamping_suppliers,
            "vehicle_models": vehicle_models,
            "versions": versions,
        }

    def _scope_cascade_query(
        self,
        query: Query[_T],
        *,
        locations: list[str] | None,
        location: str | None,
        overlap_year: int | None,
        as_of_year: int | None = None,
        as_of_month: int | None = None,
    ) -> Query[_T]:
        if locations is not None:
            query = query.filter(StampingPart.location.in_(locations))
        elif location:
            query = query.filter(StampingPart.location == location)
        if as_of_year is not None and as_of_month is not None:
            query = query.filter(
                period_hit_clause(
                    StampingPart.effective_year,
                    StampingPart.effective_month,
                    StampingPart.expiry_year,
                    StampingPart.expiry_month,
                    as_of_year,
                    as_of_month,
                )
            )
        elif overlap_year is not None:
            query = query.filter(
                period_overlaps_year_clause(
                    StampingPart.effective_year,
                    StampingPart.expiry_year,
                    overlap_year,
                )
            )
        return query

    def _distinct_string_values(self, db: Session, column: _StringColumn) -> list[str]:
        query = (
            db.query(column).distinct().filter(column.isnot(None), column != "").order_by(column)
        )
        values: list[str] = []
        for row in query.all():
            value = row[0]
            if isinstance(value, str) and value:
                values.append(value)
        return values

    def _collect_distinct_strings(
        self,
        query: Query[_T],
        column: _StringColumn,
    ) -> list[str]:
        rows = query.filter(column.isnot(None), column != "").order_by(column).all()
        values: list[str] = []
        for row in rows:
            if not isinstance(row, Sequence) or isinstance(row, str | bytes):
                continue
            value = row[0]
            if isinstance(value, str) and value:
                values.append(value)
        return values
