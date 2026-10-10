"""冲压模具费写入：插入明细、按范围删除、审核/反审。"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.stamping.die_fee import StampingDieFee
from app.models.stamping.die_fee_item import StampingDieFeeItem
from app.repositories.persist import apply_payload_fields, model_from_payload, query_update
from app.repositories.stamping.die_fee.queries import StampingDieFeeQueries
from app.schemas.dto.stamping_die_fee_dto import (
    DieFeeInsertPayload,
    DieFeeItemPayload,
    DieFeePatch,
)


class StampingDieFeeWrites:
    def __init__(self, queries: StampingDieFeeQueries | None = None) -> None:
        self._queries = queries or StampingDieFeeQueries()

    def insert_with_items(self, db: Session, payload: DieFeeInsertPayload) -> StampingDieFee:
        items = payload.items
        record = model_from_payload(StampingDieFee, payload)
        db.add(record)
        db.flush()
        for item in items:
            self._add_item(db, record.id, item)
        db.flush()
        return record

    def _add_item(self, db: Session, fee_id: int, item: DieFeeItemPayload) -> None:
        row = model_from_payload(StampingDieFeeItem, item)
        row.fee_id = fee_id
        db.add(row)

    def update_fields(self, db: Session, fee_id: int, patch: DieFeePatch) -> StampingDieFee | None:
        record = self._queries.get_by_id(db, fee_id)
        if record is None:
            return None
        apply_payload_fields(record, patch)
        db.flush()
        db.refresh(record)
        return record

    def delete_by_id(self, db: Session, record: StampingDieFee) -> None:
        db.delete(record)
        db.flush()

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
        query = self._queries._build_list_query(
            db,
            year=year,
            location=location,
            locations=locations,
            vehicle_model=vehicle_model,
            part_number=None,
            audit_status=None,
            only_zero=False,
            stamping_supplier=stamping_supplier,
            version=version,
        )
        fee_ids = [row.id for row in query.with_entities(StampingDieFee.id).all()]
        if fee_ids:
            (
                db.query(StampingDieFeeItem)
                .filter(StampingDieFeeItem.fee_id.in_(fee_ids))
                .delete(synchronize_session=False)
            )
            count = (
                db.query(StampingDieFee)
                .filter(StampingDieFee.id.in_(fee_ids))
                .delete(synchronize_session=False)
            )
        else:
            count = 0
        db.flush()
        return count

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        vehicle_model: str,
    ) -> int:
        fee_ids = [
            row.id
            for row in (
                self._queries._scope_query(
                    db, year=year, location=location, vehicle_model=vehicle_model
                )
                .filter(StampingDieFee.audit_status != AUDIT_APPROVED)
                .with_entities(StampingDieFee.id)
                .all()
            )
        ]
        if fee_ids:
            (
                db.query(StampingDieFeeItem)
                .filter(StampingDieFeeItem.fee_id.in_(fee_ids))
                .delete(synchronize_session=False)
            )
        count = (
            self._queries._scope_query(
                db, year=year, location=location, vehicle_model=vehicle_model
            )
            .filter(StampingDieFee.audit_status != AUDIT_APPROVED)
            .delete(synchronize_session=False)
        )
        db.flush()
        return count

    def approve_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        vehicle_model: str,
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
                db, year=year, location=location, vehicle_model=vehicle_model
            ).filter(StampingDieFee.audit_status.in_([AUDIT_PENDING, AUDIT_REJECTED])),
            values,
        )
        db.flush()
        return count

    def reverse_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str | None = None,
        vehicle_model: str,
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
                db, year=year, location=location, vehicle_model=vehicle_model
            ).filter(StampingDieFee.audit_status == AUDIT_APPROVED),
            values,
        )
        db.flush()
        return count
