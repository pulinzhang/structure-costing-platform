"""成品月核价 — Repository。

查询见 queries.py，写入见 writes.py，载荷形状见 payloads.py。
本文件是门面：独立查询/写入类，这里只委托。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.costing.assembly_cost import AssemblyCost
from app.repositories.costing.assembly_cost.payloads import (
    AssemblyCostFilterSummary,
    AssemblyCostIndirectInsert,
    AssemblyCostItemInsert,
    AssemblyCostListFilters,
    AssemblyCostUpsertPayload,
    SettlementAmountField,
    empty_assembly_cost_summary,
)
from app.repositories.costing.assembly_cost.queries import AssemblyCostQueries
from app.repositories.costing.assembly_cost.writes import AssemblyCostWrites

__all__ = [
    "AssemblyCostRepository",
    "AssemblyCostFilterSummary",
    "AssemblyCostIndirectInsert",
    "AssemblyCostItemInsert",
    "AssemblyCostListFilters",
    "AssemblyCostUpsertPayload",
    "SettlementAmountField",
    "empty_assembly_cost_summary",
]


class AssemblyCostRepository:
    """成品月核价结果数据访问。"""

    def __init__(self) -> None:
        self._queries = AssemblyCostQueries()
        self._writes = AssemblyCostWrites(self._queries)

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        view: str = "finance",
        level: int | None = None,
        object_kind: str | None = None,
        confirm_status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AssemblyCost], int, AssemblyCostListFilters]:
        return self._queries.paginate(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            view=view,
            level=level,
            object_kind=object_kind,
            confirm_status=confirm_status,
            skip=skip,
            limit=limit,
        )

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        view: str = "finance",
        level: int | None = None,
        object_kind: str | None = None,
        confirm_status: str | None = None,
    ) -> list[AssemblyCost]:
        return self._queries.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            view=view,
            level=level,
            object_kind=object_kind,
            confirm_status=confirm_status,
        )

    def list_ids_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        only_pending: bool = False,
        view: str = "finance",
    ) -> list[int]:
        return self._queries.list_ids_by_scope(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            only_pending=only_pending,
            view=view,
        )

    def count_approved_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> int:
        return self._queries.count_approved_by_scope(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def count_approved_by_ids(self, db: Session, ids: list[int]) -> int:
        return self._queries.count_approved_by_ids(db, ids)

    def list_by_scope_source_nodes(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        source_node_ids: list[int],
    ) -> list[AssemblyCost]:
        return self._queries.list_by_scope_source_nodes(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            source_node_ids=source_node_ids,
        )

    def list_by_part_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        part_number: str,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
    ) -> list[AssemblyCost]:
        return self._queries.list_by_part_scope(
            db,
            year=year,
            month=month,
            part_number=part_number,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def list_should_costs_for_nodes(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        months: list[tuple[int, int]],
        source_node_ids: list[int],
        amount_field: SettlementAmountField = "total_amount",
    ) -> list[tuple[int, int, int, Decimal]]:
        return self._queries.list_should_costs_for_nodes(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            months=months,
            source_node_ids=source_node_ids,
            amount_field=amount_field,
        )

    def list_distinct_years(self, db: Session) -> list[int]:
        return self._queries.list_distinct_years(db)

    def get_latest_scope_year_month(self, db: Session) -> tuple[str, str, str, int, int] | None:
        return self._queries.get_latest_scope_year_month(db)

    def get_by_id(self, db: Session, cost_id: int) -> AssemblyCost | None:
        return self._queries.get_by_id(db, cost_id)

    def get_by_business_key(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        source_node_id: int,
    ) -> AssemblyCost | None:
        return self._queries.get_by_business_key(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            source_node_id=source_node_id,
        )

    def upsert_with_children(
        self, db: Session, payload: AssemblyCostUpsertPayload
    ) -> tuple[AssemblyCost, bool]:
        return self._writes.upsert_with_children(db, payload)

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> int:
        return self._writes.delete_unaudited_by_scope(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def approve_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
    ) -> int:
        return self._writes.approve_by_scope(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            audited_by=audited_by,
            audited_at=audited_at,
            audit_remark=audit_remark,
        )

    def reverse_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str | None,
    ) -> int:
        return self._writes.reverse_by_scope(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            reverse_audited_by=reverse_audited_by,
            reverse_audited_at=reverse_audited_at,
            reverse_audit_remark=reverse_audit_remark,
        )

    def delete_by_ids(self, db: Session, ids: list[int]) -> int:
        return self._writes.delete_by_ids(db, ids)

    def approve_by_ids(
        self,
        db: Session,
        ids: list[int],
        *,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
    ) -> int:
        return self._writes.approve_by_ids(
            db, ids, audited_by=audited_by, audited_at=audited_at, audit_remark=audit_remark
        )

    def reverse_by_ids(
        self,
        db: Session,
        ids: list[int],
        *,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str | None,
    ) -> int:
        return self._writes.reverse_by_ids(
            db,
            ids,
            reverse_audited_by=reverse_audited_by,
            reverse_audited_at=reverse_audited_at,
            reverse_audit_remark=reverse_audit_remark,
        )
