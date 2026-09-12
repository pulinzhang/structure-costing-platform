"""BOM 焊接工艺拆解 Repository。

查询见 welding_process_breakdown/queries.py，写入见 writes.py。
本文件是门面：独立查询/写入类，这里只委托。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.bom import BomWeldingProcessBreakdownLine, BomWeldingProcessBreakdownNode
from app.repositories.bom.welding_process_breakdown.queries import WeldingBreakdownQueries
from app.repositories.bom.welding_process_breakdown.types import (
    WeldingBreakdownFilterSummary,
    WeldingBreakdownListFilters,
)
from app.repositories.bom.welding_process_breakdown.writes import WeldingBreakdownWrites
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownLinePatch,
    BomWeldingProcessBreakdownLineWrite,
    BomWeldingProcessBreakdownNodePatch,
    BomWeldingProcessBreakdownNodeWrite,
)

__all__ = [
    "BomWeldingProcessBreakdownRepository",
    "WeldingBreakdownFilterSummary",
    "WeldingBreakdownListFilters",
]


class BomWeldingProcessBreakdownRepository:
    """焊接工艺拆解数据访问"""

    def __init__(self) -> None:
        self._queries = WeldingBreakdownQueries()
        self._writes = WeldingBreakdownWrites(self._queries)

    def get_node_by_id(self, db: Session, node_id: int) -> BomWeldingProcessBreakdownNode | None:
        return self._queries.get_node_by_id(db, node_id)

    def map_weld_info_by_ids(self, db: Session, node_ids: list[int]) -> dict[int, str]:
        return self._queries.map_weld_info_by_ids(db, node_ids)

    def get_line_by_id(self, db: Session, line_id: int) -> BomWeldingProcessBreakdownLine | None:
        return self._queries.get_line_by_id(db, line_id)

    def paginate(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        level: int | None = None,
        audit_status: str | None = None,
        parse_status: str | None = None,
        process_line_count_eq: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[BomWeldingProcessBreakdownNode], int]:
        return self._queries.paginate(
            db,
            location=location,
            locations=locations,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=level,
            audit_status=audit_status,
            parse_status=parse_status,
            process_line_count_eq=process_line_count_eq,
            skip=skip,
            limit=limit,
        )

    def list_l0_for_export(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        process_line_count_eq: int | None = None,
    ) -> list[BomWeldingProcessBreakdownNode]:
        return self._queries.list_l0_for_export(
            db,
            location=location,
            locations=locations,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            process_line_count_eq=process_line_count_eq,
        )

    def list_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> list[BomWeldingProcessBreakdownNode]:
        return self._queries.list_by_scope(
            db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
        )

    def exists_by_bom_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> bool:
        return self._queries.exists_by_bom_scope(
            db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
        )

    def count_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> int:
        return self._queries.count_by_scope(
            db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
        )

    def count_by_filters(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        level: int | None = None,
        audit_status: str | None = None,
        parse_status: str | None = None,
        process_line_count_eq: int | None = None,
    ) -> int:
        return self._queries.count_by_filters(
            db,
            location=location,
            locations=locations,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=level,
            audit_status=audit_status,
            parse_status=parse_status,
            process_line_count_eq=process_line_count_eq,
        )

    def sum_process_line_count_by_filters(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        level: int | None = None,
        audit_status: str | None = None,
        parse_status: str | None = None,
        process_line_count_eq: int | None = None,
    ) -> int:
        return self._queries.sum_process_line_count_by_filters(
            db,
            location=location,
            locations=locations,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=level,
            audit_status=audit_status,
            parse_status=parse_status,
            process_line_count_eq=process_line_count_eq,
        )

    def summarize_by_filters(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        customer_name: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        level: int | None = None,
        audit_status: str | None = None,
        parse_status: str | None = None,
        process_line_count_eq: int | None = None,
    ) -> WeldingBreakdownFilterSummary:
        return self._queries.summarize_by_filters(
            db,
            location=location,
            locations=locations,
            customer_name=customer_name,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            level=level,
            audit_status=audit_status,
            parse_status=parse_status,
            process_line_count_eq=process_line_count_eq,
        )

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        statuses: list[str],
    ) -> int:
        return self._queries.count_by_scope_and_statuses(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            statuses=statuses,
        )

    def get_distinct_locations(self, db: Session) -> list[str]:
        return self._queries.get_distinct_locations(db)

    def get_distinct_bom_versions(
        self,
        db: Session,
        *,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        return self._queries.get_distinct_bom_versions(
            db, location=location, locations=locations, vehicle_model=vehicle_model
        )

    def get_distinct_customer_names(self, db: Session) -> list[str]:
        return self._queries.get_distinct_customer_names(db)

    def create_node(
        self,
        db: Session,
        data: BomWeldingProcessBreakdownNodeWrite,
    ) -> BomWeldingProcessBreakdownNode:
        return self._writes.create_node(db, data)

    def create_line(
        self,
        db: Session,
        data: BomWeldingProcessBreakdownLineWrite,
    ) -> BomWeldingProcessBreakdownLine:
        return self._writes.create_line(db, data)

    def update_node(
        self,
        db: Session,
        node_id: int,
        update_data: BomWeldingProcessBreakdownNodePatch,
    ) -> BomWeldingProcessBreakdownNode | None:
        return self._writes.update_node(db, node_id, update_data)

    def update_line(
        self,
        db: Session,
        line_id: int,
        update_data: BomWeldingProcessBreakdownLinePatch,
    ) -> BomWeldingProcessBreakdownLine | None:
        return self._writes.update_line(db, line_id, update_data)

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> int:
        return self._writes.delete_unaudited_by_scope(
            db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
        )

    def approve_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
        updated_by: str | None = None,
    ) -> int:
        return self._writes.approve_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            audited_by=audited_by,
            audited_at=audited_at,
            audit_remark=audit_remark,
            updated_by=updated_by,
        )

    def reverse_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: str | None = None,
    ) -> int:
        return self._writes.reverse_by_scope(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            reverse_audited_by=reverse_audited_by,
            reverse_audited_at=reverse_audited_at,
            reverse_audit_remark=reverse_audit_remark,
            updated_by=updated_by,
        )
