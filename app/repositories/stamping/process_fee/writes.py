"""冲压加工费写入：upsert、替换分项、按范围删未审、审核/反审。"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.stamping import StampingProcessFee, StampingProcessFeeItem
from app.repositories.persist import apply_payload_fields, model_from_payload, query_update
from app.repositories.stamping.process_fee.queries import StampingProcessFeeQueries
from app.schemas.dto.stamping_process_fee_dto import (
    ProcessFeeItemPayload,
    ProcessFeePatch,
    ProcessFeeUpsertPayload,
)

logger = logging.getLogger("repository.stamping")

_UPSERT_SKIP = frozenset({"id", "created_by", "created_at"})


class StampingProcessFeeWrites:
    def __init__(self, queries: StampingProcessFeeQueries | None = None) -> None:
        self._queries = queries or StampingProcessFeeQueries()

    def replace_items(
        self,
        db: Session,
        fee_id: int,
        items_data: list[ProcessFeeItemPayload],
    ) -> None:
        """整表替换某加工费行的工序分项。"""
        record = (
            db.query(StampingProcessFee)
            .options(joinedload(StampingProcessFee.process_items))
            .filter(StampingProcessFee.id == fee_id)
            .first()
        )
        if record is None:
            return
        record.process_items.clear()
        for item in items_data:
            record.process_items.append(model_from_payload(StampingProcessFeeItem, item))
        db.flush()

    def upsert(self, db: Session, data: ProcessFeeUpsertPayload) -> StampingProcessFee:
        existing = self._queries.get_by_business_key(
            db,
            year=data.year,
            location=data.location,
            stamping_supplier=data.stamping_supplier or "",
            vehicle_model=data.vehicle_model,
            version=data.version,
            part_number=data.snapshot.part_number,
        )
        if existing:
            apply_payload_fields(existing, data, skip=_UPSERT_SKIP)
            apply_payload_fields(existing, data.snapshot)
            db.flush()
            self.replace_items(db, existing.id, data.process_items)
            return existing

        record = model_from_payload(StampingProcessFee, data)
        apply_payload_fields(record, data.snapshot)
        if not record.audit_status:
            record.audit_status = AUDIT_PENDING
        db.add(record)
        db.flush()
        self.replace_items(db, record.id, data.process_items)
        return record

    def update_fields(
        self, db: Session, fee_id: int, update_data: ProcessFeePatch
    ) -> StampingProcessFee | None:
        record = self._queries.get_by_id(db, fee_id)
        if not record:
            return None
        apply_payload_fields(record, update_data)
        db.flush()
        db.refresh(record)
        return record

    def bulk_upsert(
        self, db: Session, data_list: list[ProcessFeeUpsertPayload]
    ) -> list[StampingProcessFee]:
        records = [self.upsert(db, data) for data in data_list]
        db.flush()
        for record in records:
            db.refresh(record)
        logger.info("批量 upsert 冲压加工费: %s 条", len(records))
        return records

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
        fee_ids = [
            row.id
            for row in (
                self._queries._scope_query(
                    db,
                    year=year,
                    location=location,
                    stamping_supplier=stamping_supplier,
                    vehicle_model=vehicle_model,
                    version=version,
                )
                .filter(StampingProcessFee.audit_status != AUDIT_APPROVED)
                .with_entities(StampingProcessFee.id)
                .all()
            )
        ]
        if fee_ids:
            (
                db.query(StampingProcessFeeItem)
                .filter(StampingProcessFeeItem.fee_id.in_(fee_ids))
                .delete(synchronize_session=False)
            )
        count = (
            self._queries._scope_query(
                db,
                year=year,
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
                version=version,
            )
            .filter(StampingProcessFee.audit_status != AUDIT_APPROVED)
            .delete(synchronize_session=False)
        )
        db.flush()
        logger.info(
            "批量删除未审核冲压加工费: year=%s location=%s supplier=%s count=%s",
            year,
            location,
            stamping_supplier,
            count,
        )
        return count

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
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
                version=version,
            ).filter(StampingProcessFee.audit_status.in_([AUDIT_PENDING, AUDIT_REJECTED])),
            values,
        )
        db.flush()
        return count

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
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
                version=version,
            ).filter(StampingProcessFee.audit_status == AUDIT_APPROVED),
            values,
        )
        db.flush()
        return count
