"""冲压加工费结果 Repository。

查询见 process_fee/queries.py，写入见 writes.py。
本文件是门面：独立查询/写入类，这里只委托。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.stamping import StampingProcessFee
from app.repositories.stamping.process_fee.queries import StampingProcessFeeQueries
from app.repositories.stamping.process_fee.types import (
    ProcessFeeFilterSummary,
    ProcessFeeListFilters,
)
from app.repositories.stamping.process_fee.writes import StampingProcessFeeWrites
from app.schemas.dto.stamping_process_fee_dto import (
    ProcessFeeItemPayload,
    ProcessFeePatch,
    ProcessFeeUpsertPayload,
)

__all__ = [
    "StampingProcessFeeRepository",
    "ProcessFeeFilterSummary",
    "ProcessFeeListFilters",
]


class StampingProcessFeeRepository:
    """冲压加工费结果数据访问"""

    def __init__(self) -> None:
        self._queries = StampingProcessFeeQueries()
        self._writes = StampingProcessFeeWrites(self._queries)

    def get_by_id(self, db: Session, fee_id: int) -> StampingProcessFee | None:
        return self._queries.get_by_id(db, fee_id)

    def list_by_ids(self, db: Session, fee_ids: list[int]) -> list[StampingProcessFee]:
        return self._queries.list_by_ids(db, fee_ids)

    def get_by_business_key(
        self,
        db: Session,
        year: int,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
        part_number: str,
    ) -> StampingProcessFee | None:
        return self._queries.get_by_business_key(
            db, year, location, stamping_supplier, vehicle_model, version, part_number
        )

    def paginate(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        only_zero: bool = False,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StampingProcessFee], int]:
        return self._queries.paginate(
            db,
            year,
            location,
            locations,
            stamping_supplier,
            stamping_suppliers,
            vehicle_model,
            version,
            part_number,
            audit_status,
            only_zero,
            skip,
            limit,
        )

    def summarize_by_filters(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> ProcessFeeFilterSummary:
        return self._queries.summarize_by_filters(
            db,
            year,
            location,
            locations,
            stamping_supplier,
            stamping_suppliers,
            vehicle_model,
            version,
            part_number,
            audit_status,
        )

    def list_for_export(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> list[StampingProcessFee]:
        return self._queries.list_for_export(
            db,
            year,
            location,
            locations,
            stamping_supplier,
            stamping_suppliers,
            vehicle_model,
            version,
            part_number,
            audit_status,
        )

    def list_tailor_weld_missing_other_fee_part_numbers(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        statuses: list[str],
    ) -> list[str]:
        return self._queries.list_tailor_weld_missing_other_fee_part_numbers(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            statuses=statuses,
        )

    def list_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> list[StampingProcessFee]:
        return self._queries.list_by_scope(
            db, year=year, location=location, vehicle_model=vehicle_model, version=version
        )

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        statuses: list[str],
    ) -> int:
        return self._queries.count_by_scope_and_statuses(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            statuses=statuses,
        )

    def get_distinct_years(self, db: Session) -> list[int]:
        return self._queries.get_distinct_years(db)

    def get_distinct_locations(self, db: Session, year: int | None = None) -> list[str]:
        return self._queries.get_distinct_locations(db, year)

    def get_distinct_suppliers(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> list[str]:
        return self._queries.get_distinct_suppliers(
            db, year, location, locations, vehicle_model, version
        )

    def get_distinct_versions(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        return self._queries.get_distinct_versions(
            db, year, location, locations, stamping_supplier, vehicle_model
        )

    def replace_items(
        self,
        db: Session,
        fee_id: int,
        items_data: list[ProcessFeeItemPayload],
    ) -> None:
        return self._writes.replace_items(db, fee_id, items_data)

    def upsert(self, db: Session, data: ProcessFeeUpsertPayload) -> StampingProcessFee:
        return self._writes.upsert(db, data)

    def update_fields(
        self, db: Session, fee_id: int, update_data: ProcessFeePatch
    ) -> StampingProcessFee | None:
        return self._writes.update_fields(db, fee_id, update_data)

    def bulk_upsert(
        self, db: Session, data_list: list[ProcessFeeUpsertPayload]
    ) -> list[StampingProcessFee]:
        return self._writes.bulk_upsert(db, data_list)

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> int:
        return self._writes.delete_unaudited_by_scope(
            db,
            year=year,
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
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            reverse_audited_by=reverse_audited_by,
            reverse_audited_at=reverse_audited_at,
            reverse_audit_remark=reverse_audit_remark,
            updated_by=updated_by,
        )
