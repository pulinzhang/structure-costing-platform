"""采购对象清单 Repository。

查询见 procurement_object/queries.py，写入见 writes.py。
本文件是门面：独立查询/写入类，这里只委托。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.bom.procurement_object import BomProcurementObject, BomProcurementObjectList
from app.models.bom.procurement_object_generate_log import BomProcurementObjectGenerateLog
from app.repositories.bom.procurement_object.queries import BomProcurementObjectQueries
from app.repositories.bom.procurement_object.types import (
    ProcurementObjectAuditSummary,
    ProcurementObjectScopeFilters,
    empty_procurement_object_summary,
    object_scope_filters,
)
from app.repositories.bom.procurement_object.writes import BomProcurementObjectWrites
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectGenerateLogWrite,
    BomProcurementObjectListWrite,
    BomProcurementObjectWrite,
)

__all__ = [
    "BomProcurementObjectRepository",
    "ProcurementObjectAuditSummary",
    "ProcurementObjectScopeFilters",
    "empty_procurement_object_summary",
    "object_scope_filters",
]


class BomProcurementObjectRepository:
    """采购对象清单数据访问。"""

    def __init__(self) -> None:
        self._queries = BomProcurementObjectQueries()
        self._writes = BomProcurementObjectWrites(self._queries)

    def get_list_by_id(self, db: Session, list_id: int) -> BomProcurementObjectList | None:
        return self._queries.get_list_by_id(db, list_id)

    def get_list_by_snapshot_id(
        self, db: Session, snapshot_id: int
    ) -> BomProcurementObjectList | None:
        return self._queries.get_list_by_snapshot_id(db, snapshot_id)

    def has_list_for_location(self, db: Session, location: str) -> bool:
        return self._queries.has_list_for_location(db, location)

    def get_list_by_scope(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomProcurementObjectList | None:
        return self._queries.get_list_by_scope(
            db, location=location, vehicle_model=vehicle_model, bom_version=bom_version
        )

    def list_lists_by_location_vehicle(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[BomProcurementObjectList]:
        return self._queries.list_lists_by_location_vehicle(
            db, location=location, vehicle_model=vehicle_model
        )

    def list_objects_by_location_vehicle(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
    ) -> list[BomProcurementObject]:
        return self._queries.list_objects_by_location_vehicle(
            db, location=location, vehicle_model=vehicle_model
        )

    def get_latest_list(self, db: Session) -> BomProcurementObjectList | None:
        return self._queries.get_latest_list(db)

    def get_object_by_id(self, db: Session, object_id: int) -> BomProcurementObject | None:
        return self._queries.get_object_by_id(db, object_id)

    def get_confirm_status_by_id(self, db: Session, object_id: int) -> str | None:
        return self._queries.get_confirm_status_by_id(db, object_id)

    def map_confirm_status_by_ids(self, db: Session, object_ids: list[int]) -> dict[int, str]:
        return self._queries.map_confirm_status_by_ids(db, object_ids)

    def list_objects_by_list_id(self, db: Session, list_id: int) -> list[BomProcurementObject]:
        return self._queries.list_objects_by_list_id(db, list_id)

    def count_approved_objects(self, db: Session, list_id: int) -> int:
        return self._queries.count_approved_objects(db, list_id)

    def paginate_objects(
        self,
        db: Session,
        *,
        scope: ProcurementObjectScopeFilters,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomProcurementObject], int]:
        return self._queries.paginate_objects(db, scope=scope, skip=skip, limit=limit)

    def list_objects_for_export(
        self,
        db: Session,
        *,
        scope: ProcurementObjectScopeFilters,
    ) -> list[BomProcurementObject]:
        return self._queries.list_objects_for_export(db, scope=scope)

    def get_filter_options(self, db: Session) -> tuple[list[str], list[str], list[str]]:
        return self._queries.get_filter_options(db)

    def summarize_objects(
        self,
        db: Session,
        *,
        scope: ProcurementObjectScopeFilters,
    ) -> ProcurementObjectAuditSummary:
        return self._queries.summarize_objects(db, scope=scope)

    def map_l0_periods(
        self,
        db: Session,
        *,
        snapshot_l0_keys: list[tuple[int, str]],
    ) -> dict[tuple[int, str], tuple[int, int, int | None, int | None]]:
        return self._queries.map_l0_periods(db, snapshot_l0_keys=snapshot_l0_keys)

    def get_generate_log_by_id(
        self, db: Session, log_id: int
    ) -> BomProcurementObjectGenerateLog | None:
        return self._queries.get_generate_log_by_id(db, log_id)

    def paginate_generate_logs(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomProcurementObjectGenerateLog], int]:
        return self._queries.paginate_generate_logs(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            skip=skip,
            limit=limit,
        )

    def create_list(
        self, db: Session, payload: BomProcurementObjectListWrite
    ) -> BomProcurementObjectList:
        return self._writes.create_list(db, payload)

    def bulk_create_objects(
        self, db: Session, payloads: list[BomProcurementObjectWrite]
    ) -> list[int]:
        return self._writes.bulk_create_objects(db, payloads)

    def delete_list(self, db: Session, header: BomProcurementObjectList) -> None:
        return self._writes.delete_list(db, header)

    def delete_object(self, db: Session, row: BomProcurementObject) -> None:
        return self._writes.delete_object(db, row)

    def approve_objects_by_list_id(
        self,
        db: Session,
        *,
        list_id: int,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str,
        updated_by: str,
    ) -> int:
        return self._writes.approve_objects_by_list_id(
            db,
            list_id=list_id,
            audited_by=audited_by,
            audited_at=audited_at,
            audit_remark=audit_remark,
            updated_by=updated_by,
        )

    def reverse_objects_by_list_id(
        self,
        db: Session,
        *,
        list_id: int,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: str,
    ) -> int:
        return self._writes.reverse_objects_by_list_id(
            db,
            list_id=list_id,
            reverse_audited_by=reverse_audited_by,
            reverse_audited_at=reverse_audited_at,
            reverse_audit_remark=reverse_audit_remark,
            updated_by=updated_by,
        )

    def delete_pending_objects_by_list_id(self, db: Session, list_id: int) -> int:
        return self._writes.delete_pending_objects_by_list_id(db, list_id)

    def recount_header_from_rows(self, db: Session, header: BomProcurementObjectList) -> None:
        return self._writes.recount_header_from_rows(db, header)

    def create_generate_log(
        self, db: Session, data: BomProcurementObjectGenerateLogWrite
    ) -> BomProcurementObjectGenerateLog:
        return self._writes.create_generate_log(db, data)
