"""冲压零件核价写入：upsert、按范围删未审、审核/反审。"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.costing import StampingPartCost
from app.repositories.costing.stamping_part_cost.queries import StampingPartCostQueries
from app.repositories.persist import apply_payload_fields, model_from_payload, query_update
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostPatch,
    StampingPartCostUpsertPayload,
)

logger = logging.getLogger("repository.stamping_part_cost")

_UPSERT_SKIP = frozenset({"id", "created_by", "created_at"})


class StampingPartCostWrites:
    def __init__(self, queries: StampingPartCostQueries | None = None) -> None:
        self._queries = queries or StampingPartCostQueries()

    def upsert(self, db: Session, data: StampingPartCostUpsertPayload) -> StampingPartCost:
        existing = self._queries.get_by_business_key(
            db,
            year=data.year,
            month=data.month,
            location=data.location,
            stamping_supplier=data.stamping_supplier,
            vehicle_model=data.vehicle_model,
            version=data.version,
            part_number=data.snapshot.part_number,
        )
        if existing:
            apply_payload_fields(existing, data, skip=_UPSERT_SKIP)
            apply_payload_fields(existing, data.snapshot)
            db.flush()
            return existing

        record = model_from_payload(StampingPartCost, data)
        apply_payload_fields(record, data.snapshot)
        if not record.audit_status:
            record.audit_status = AUDIT_PENDING
        db.add(record)
        db.flush()
        return record

    def update_fields(
        self, db: Session, cost_id: int, update_data: StampingPartCostPatch
    ) -> StampingPartCost | None:
        record = self._queries.get_by_id(db, cost_id)
        if not record:
            return None
        apply_payload_fields(record, update_data)
        db.flush()
        db.refresh(record)
        return record

    def bulk_upsert(
        self, db: Session, data_list: list[StampingPartCostUpsertPayload]
    ) -> list[StampingPartCost]:
        records = [self.upsert(db, data) for data in data_list]
        db.flush()
        for record in records:
            db.refresh(record)
        logger.info("批量 upsert 零件价格核算: %s 条", len(records))
        return records

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
        count = (
            self._queries._scope_query(
                db,
                year=year,
                month=month,
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
                version=version,
            )
            .filter(StampingPartCost.audit_status != AUDIT_APPROVED)
            .delete(synchronize_session=False)
        )
        db.flush()
        logger.info(
            "批量删除未审核零件价格核算: year=%s month=%s location=%s vehicle=%s "
            "version=%s supplier=%s count=%s",
            year,
            month,
            location,
            vehicle_model,
            version,
            stamping_supplier,
            count,
        )
        return count

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
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_APPROVED,
            "audited_by": audited_by,
            "audited_at": audited_at,
            "audit_remark": audit_remark,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by
        count = query_update(
            self._queries._scope_query(
                db,
                year=year,
                month=month,
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
                version=version,
            ).filter(StampingPartCost.audit_status.in_([AUDIT_PENDING, AUDIT_REJECTED])),
            values,
        )
        db.flush()
        return count

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
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_PENDING,
            "reverse_audited_by": reverse_audited_by,
            "reverse_audited_at": reverse_audited_at,
            "reverse_audit_remark": reverse_audit_remark,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by
        count = query_update(
            self._queries._scope_query(
                db,
                year=year,
                month=month,
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
                version=version,
            ).filter(StampingPartCost.audit_status == AUDIT_APPROVED),
            values,
        )
        db.flush()
        return count
