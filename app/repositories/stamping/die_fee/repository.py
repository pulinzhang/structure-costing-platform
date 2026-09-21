"""冲压年度模具费仓储。查询见 queries.py，写入见 writes.py。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.stamping.die_fee import StampingDieFee
from app.repositories.stamping.die_fee.queries import StampingDieFeeQueries
from app.repositories.stamping.die_fee.types import DieFeeFilterSummary
from app.repositories.stamping.die_fee.writes import StampingDieFeeWrites
from app.schemas.dto.stamping_die_fee_dto import DieFeeInsertPayload, DieFeePatch

__all__ = [
    "StampingDieFeeRepository",
    "DieFeeFilterSummary",
]


class StampingDieFeeRepository:
    """冲压年度模具费数据访问。"""

    def __init__(self) -> None:
        self._queries = StampingDieFeeQueries()
        self._writes = StampingDieFeeWrites(self._queries)

    def get_by_id(self, db: Session, fee_id: int) -> StampingDieFee | None:
        return self._queries.get_by_id(db, fee_id)

    def list_by_ids(self, db: Session, fee_ids: list[int]) -> list[StampingDieFee]:
        return self._queries.list_by_ids(db, fee_ids)

    def get_by_year_location_vehicle_part(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str,
        part_number: str,
    ) -> StampingDieFee | None:
        return self._queries.get_by_year_location_vehicle_part(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            part_number=part_number,
        )

    def list_by_part_from_year(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        part_number: str,
        from_year: int,
    ) -> list[StampingDieFee]:
        return self._queries.list_by_part_from_year(
            db,
            location=location,
            vehicle_model=vehicle_model,
            part_number=part_number,
            from_year=from_year,
        )

    def count_by_year_location(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str | None = None,
    ) -> int:
        return self._queries.count_by_year_location(
            db, year=year, location=location, vehicle_model=vehicle_model
        )

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str,
        statuses: list[str],
        stamping_supplier: str | None = None,
        version: str | None = None,
    ) -> int:
        return self._queries.count_by_scope_and_statuses(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            statuses=statuses,
            stamping_supplier=stamping_supplier,
            version=version,
        )

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        part_number: str | None,
        audit_status: str | None,
        only_zero: bool,
        skip: int,
        limit: int,
        stamping_supplier: str | None = None,
        version: str | None = None,
    ) -> tuple[list[StampingDieFee], int]:
        return self._queries.paginate(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=only_zero,
            skip=skip,
            limit=limit,
            stamping_supplier=stamping_supplier,
            version=version,
        )

    def summarize_by_filters(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        part_number: str | None,
        audit_status: str | None,
        stamping_supplier: str | None = None,
        version: str | None = None,
    ) -> DieFeeFilterSummary:
        return self._queries.summarize_by_filters(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            part_number=part_number,
            audit_status=audit_status,
            stamping_supplier=stamping_supplier,
            version=version,
        )

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        part_number: str | None,
        audit_status: str | None,
        only_zero: bool,
        stamping_supplier: str | None = None,
        version: str | None = None,
    ) -> list[StampingDieFee]:
        return self._queries.list_for_export(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=only_zero,
            stamping_supplier=stamping_supplier,
            version=version,
        )

    def get_distinct_years(self, db: Session) -> list[int]:
        return self._queries.get_distinct_years(db)

    def list_distinct_suppliers(
        self,
        db: Session,
        *,
        year: int | None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None,
    ) -> list[str]:
        return self._queries.list_distinct_suppliers(
            db, year=year, location=location, locations=locations, vehicle_model=vehicle_model
        )

    def map_final_die_fee_by_part_numbers(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        part_numbers: list[str],
    ) -> dict[str, tuple[Decimal, Decimal]]:
        return self._queries.map_final_die_fee_by_part_numbers(
            db, year=year, location=location, vehicle_model=vehicle_model, part_numbers=part_numbers
        )

    def list_distinct_versions(
        self,
        db: Session,
        *,
        year: int | None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None,
        stamping_supplier: str | None = None,
    ) -> list[str]:
        return self._queries.list_distinct_versions(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            stamping_supplier=stamping_supplier,
        )

    def insert_with_items(self, db: Session, payload: DieFeeInsertPayload) -> StampingDieFee:
        return self._writes.insert_with_items(db, payload)

    def update_fields(self, db: Session, fee_id: int, patch: DieFeePatch) -> StampingDieFee | None:
        return self._writes.update_fields(db, fee_id, patch)

    def delete_by_id(self, db: Session, record: StampingDieFee) -> None:
        return self._writes.delete_by_id(db, record)

    def delete_all_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str,
        stamping_supplier: str | None = None,
        version: str | None = None,
    ) -> int:
        return self._writes.delete_all_by_scope(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            stamping_supplier=stamping_supplier,
            version=version,
        )

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str,
    ) -> int:
        return self._writes.delete_unaudited_by_scope(
            db, year=year, location=location, locations=locations, vehicle_model=vehicle_model
        )

    def approve_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
        updated_by: str | None = None,
    ) -> int:
        return self._writes.approve_by_scope(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
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
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: str | None = None,
    ) -> int:
        return self._writes.reverse_by_scope(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            reverse_audited_by=reverse_audited_by,
            reverse_audited_at=reverse_audited_at,
            reverse_audit_remark=reverse_audit_remark,
            updated_by=updated_by,
        )
