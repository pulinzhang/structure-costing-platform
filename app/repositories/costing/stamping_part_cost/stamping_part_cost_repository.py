"""冲压零件价格核算结果 Repository。

查询见 queries.py，写入见 writes.py，形状见 types.py。
本文件是门面：独立查询/写入类，这里只委托。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.costing import StampingPartCost
from app.repositories.costing.stamping_part_cost.queries import StampingPartCostQueries
from app.repositories.costing.stamping_part_cost.types import (
    PartCostFilterSummary,
    PartCostListFilters,
    empty_part_cost_summary,
)
from app.repositories.costing.stamping_part_cost.writes import StampingPartCostWrites
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostPatch,
    StampingPartCostUpsertPayload,
)

__all__ = [
    "StampingPartCostRepository",
    "PartCostFilterSummary",
    "PartCostListFilters",
    "empty_part_cost_summary",
]


class StampingPartCostRepository:
    """零件价格核算结果数据访问。"""

    def __init__(self) -> None:
        self._queries = StampingPartCostQueries()
        self._writes = StampingPartCostWrites(self._queries)

    def get_by_id(self, db: Session, cost_id: int) -> StampingPartCost | None:
        return self._queries.get_by_id(db, cost_id)

    def get_by_business_key(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
        part_number: str,
    ) -> StampingPartCost | None:
        return self._queries.get_by_business_key(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
        )

    def paginate(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StampingPartCost], int]:
        return self._queries.paginate(
            db,
            year,
            month,
            location,
            locations,
            stamping_supplier,
            stamping_suppliers,
            vehicle_model,
            version,
            part_number,
            audit_status,
            skip,
            limit,
        )

    def summarize_by_filters(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> PartCostFilterSummary:
        return self._queries.summarize_by_filters(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )

    def list_for_export(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> list[StampingPartCost]:
        return self._queries.list_for_export(
            db,
            year,
            month,
            location,
            locations,
            stamping_supplier,
            stamping_suppliers,
            vehicle_model,
            version,
            part_number,
            audit_status,
        )

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        statuses: list[str],
    ) -> int:
        return self._queries.count_by_scope_and_statuses(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            statuses=statuses,
        )

    def get_distinct_years(self, db: Session) -> list[int]:
        return self._queries.get_distinct_years(db)

    def get_distinct_months(self, db: Session, year: int | None = None) -> list[int]:
        return self._queries.get_distinct_months(db, year)

    def count_calc_success_with_unit_cost(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
    ) -> int:
        return self._queries.count_calc_success_with_unit_cost(
            db, year=year, month=month, location=location, vehicle_model=vehicle_model
        )

    def list_calc_success_with_unit_cost(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
    ) -> list[StampingPartCost]:
        return self._queries.list_calc_success_with_unit_cost(
            db, year=year, month=month, location=location, vehicle_model=vehicle_model
        )

    def list_success_by_part_numbers(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        part_numbers: list[str],
    ) -> list[StampingPartCost]:
        return self._queries.list_success_by_part_numbers(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            part_numbers=part_numbers,
        )

    def get_distinct_locations(
        self, db: Session, year: int | None = None, month: int | None = None
    ) -> list[str]:
        return self._queries.get_distinct_locations(db, year, month)

    def get_distinct_suppliers(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> list[str]:
        return self._queries.get_distinct_suppliers(
            db, year, month, location, locations, vehicle_model, version
        )

    def get_distinct_versions(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        stamping_supplier: str | None = None,
    ) -> list[str]:
        return self._queries.get_distinct_versions(
            db, year, month, location, locations, vehicle_model, stamping_supplier
        )

    def upsert(self, db: Session, data: StampingPartCostUpsertPayload) -> StampingPartCost:
        return self._writes.upsert(db, data)

    def update_fields(
        self, db: Session, cost_id: int, update_data: StampingPartCostPatch
    ) -> StampingPartCost | None:
        return self._writes.update_fields(db, cost_id, update_data)

    def bulk_upsert(
        self, db: Session, data_list: list[StampingPartCostUpsertPayload]
    ) -> list[StampingPartCost]:
        return self._writes.bulk_upsert(db, data_list)

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> int:
        return self._writes.delete_unaudited_by_scope(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )

    def approve_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
        updated_by: str | None = None,
    ) -> int:
        return self._writes.approve_by_scope(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            audited_by=audited_by,
            audited_at=audited_at,
            audit_remark=audit_remark,
            updated_by=updated_by,
        )

    def reverse_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: str | None = None,
    ) -> int:
        return self._writes.reverse_by_scope(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            reverse_audited_by=reverse_audited_by,
            reverse_audited_at=reverse_audited_at,
            reverse_audit_remark=reverse_audit_remark,
            updated_by=updated_by,
        )
