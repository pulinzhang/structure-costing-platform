"""BOM 焊接费结果 Repository。

查询见 welding_fee/queries.py，写入见 writes.py。
本文件是门面：独立查询/写入类，这里只委托。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.bom import BomWeldingFee
from app.repositories.bom.welding_fee.queries import BomWeldingFeeQueries
from app.repositories.bom.welding_fee.types import WeldingFeeFilterSummary
from app.repositories.bom.welding_fee.writes import BomWeldingFeeWrites
from app.schemas.dto.bom_welding_fee_dto import (
    BomWeldingFeeItemPayload,
    BomWeldingFeeUpsertPayload,
    WeldingFeePatch,
)

__all__ = [
    "BomWeldingFeeRepository",
    "WeldingFeeFilterSummary",
]


class BomWeldingFeeRepository:
    """焊接费结果数据访问"""

    def __init__(self) -> None:
        self._queries = BomWeldingFeeQueries()
        self._writes = BomWeldingFeeWrites(self._queries)

    def get_by_id(self, db: Session, fee_id: int) -> BomWeldingFee | None:
        return self._queries.get_by_id(db, fee_id)

    def get_by_business_key(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        source_breakdown_node_id: int | None,
    ) -> BomWeldingFee | None:
        return self._queries.get_by_business_key(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            source_breakdown_node_id=source_breakdown_node_id,
        )

    def count_by_calc_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        source_node_ids: set[int] | None = None,
        level: int | None = None,
    ) -> int:
        return self._queries.count_by_calc_scope(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            level=level,
        )

    def list_by_calc_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        source_node_ids: set[int] | None = None,
        level: int | None = None,
    ) -> list[BomWeldingFee]:
        return self._queries.list_by_calc_scope(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            level=level,
        )

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        source_node_ids: set[int] | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomWeldingFee], int]:
        return self._queries.paginate(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            level=level,
            levels=levels,
            skip=skip,
            limit=limit,
        )

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        source_node_ids: set[int] | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
        ids: list[int] | None = None,
    ) -> list[BomWeldingFee]:
        return self._queries.list_for_export(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            level=level,
            levels=levels,
            ids=ids,
        )

    def summarize_by_filters(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        source_node_ids: set[int] | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
    ) -> WeldingFeeFilterSummary:
        return self._queries.summarize_by_filters(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            level=level,
            levels=levels,
        )

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        source_node_ids: set[int] | None = None,
        statuses: list[str],
        level: int | None = None,
        levels: list[int] | None = None,
    ) -> int:
        return self._queries.count_by_scope_and_statuses(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            statuses=statuses,
            level=level,
            levels=levels,
        )

    def get_distinct_years(self, db: Session) -> list[int]:
        return self._queries.get_distinct_years(db)

    def get_distinct_locations(self, db: Session, year: int | None = None) -> list[str]:
        return self._queries.get_distinct_locations(db, year)

    def replace_items(
        self,
        db: Session,
        fee_id: int,
        items_data: list[BomWeldingFeeItemPayload],
    ) -> None:
        return self._writes.replace_items(db, fee_id, items_data)

    def upsert(self, db: Session, data: BomWeldingFeeUpsertPayload) -> tuple[BomWeldingFee, bool]:
        return self._writes.upsert(db, data)

    def update_fields(
        self, db: Session, fee_id: int, update_data: WeldingFeePatch
    ) -> BomWeldingFee | None:
        return self._writes.update_fields(db, fee_id, update_data)

    def bulk_upsert(
        self, db: Session, data_list: list[BomWeldingFeeUpsertPayload]
    ) -> tuple[list[BomWeldingFee], int, int]:
        return self._writes.bulk_upsert(db, data_list)

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        source_node_ids: set[int] | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
    ) -> int:
        return self._writes.delete_unaudited_by_scope(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            level=level,
            levels=levels,
        )

    def approve_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        source_node_ids: set[int] | None = None,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
        updated_by: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
    ) -> int:
        return self._writes.approve_by_scope(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            audited_by=audited_by,
            audited_at=audited_at,
            audit_remark=audit_remark,
            updated_by=updated_by,
            level=level,
            levels=levels,
        )

    def reverse_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        source_node_ids: set[int] | None = None,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: str | None = None,
        level: int | None = None,
        levels: list[int] | None = None,
    ) -> int:
        return self._writes.reverse_by_scope(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            reverse_audited_by=reverse_audited_by,
            reverse_audited_at=reverse_audited_at,
            reverse_audit_remark=reverse_audit_remark,
            updated_by=updated_by,
            level=level,
            levels=levels,
        )
