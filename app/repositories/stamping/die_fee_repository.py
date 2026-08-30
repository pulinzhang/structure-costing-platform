"""冲压年度模具费 Repository。"""

from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import case, func

from sqlalchemy.orm import Query, Session, joinedload, noload

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.stamping.die_fee import StampingDieFee
from app.models.stamping.die_fee_item import StampingDieFeeItem
from app.repositories.persist import apply_payload_fields, model_from_payload, query_update
from app.schemas.dto.stamping_die_fee_dto import (
    DieFeeInsertPayload,
    DieFeeItemPayload,
    DieFeePatch,
)


class DieFeeFilterSummary(TypedDict):
    total_count: int
    pending_count: int
    approved_count: int
    zero_count: int
    total_fee: Decimal
    avg_fee: Decimal


def _sql_money(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


class StampingDieFeeRepository:
    def get_by_id(self, db: Session, fee_id: int) -> StampingDieFee | None:
        return (
            db.query(StampingDieFee)
            .options(joinedload(StampingDieFee.items))
            .filter(StampingDieFee.id == fee_id)
            .first()
        )

    def _scope_query(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
    ) -> Query[StampingDieFee]:
        return db.query(StampingDieFee).filter(
            StampingDieFee.year == year,
            StampingDieFee.location == location,
            StampingDieFee.vehicle_model == vehicle_model,
        )

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        statuses: list[str],
    ) -> int:
        return (
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
            )
            .filter(StampingDieFee.audit_status.in_(statuses))
            .count()
        )

    def _build_list_query(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        part_number: str | None,
        audit_status: str | None,
        only_zero: bool,
    ) -> Query[StampingDieFee]:
        query = self._scope_query(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
        )
        if part_number:
            query = query.filter(StampingDieFee.part_number.like(f"%{part_number}%"))
        if audit_status:
            query = query.filter(StampingDieFee.audit_status == audit_status)
        if only_zero:
            query = query.filter(StampingDieFee.final_die_fee == 0)
        return query

    def paginate(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        part_number: str | None,
        audit_status: str | None,
        only_zero: bool,
        skip: int,
        limit: int,
    ) -> tuple[list[StampingDieFee], int]:
        query = self._build_list_query(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=only_zero,
        )
        total = query.count()
        rows = (
            query.options(noload(StampingDieFee.items))
            .order_by(
                StampingDieFee.location.asc(),
                StampingDieFee.vehicle_model.asc(),
                StampingDieFee.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def summarize_by_filters(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        part_number: str | None,
        audit_status: str | None,
    ) -> DieFeeFilterSummary:
        query = self._build_list_query(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=False,
        )
        row = query.with_entities(
            func.count(StampingDieFee.id).label("total_count"),
            func.coalesce(func.sum(StampingDieFee.final_die_fee), 0).label("total_fee"),
            func.sum(case((StampingDieFee.audit_status == AUDIT_PENDING, 1), else_=0)).label(
                "pending_count"
            ),
            func.sum(case((StampingDieFee.audit_status == AUDIT_APPROVED, 1), else_=0)).label(
                "approved_count"
            ),
            func.sum(case((StampingDieFee.final_die_fee == 0, 1), else_=0)).label("zero_count"),
        ).one()
        total_count = int(row.total_count or 0)
        total_fee = _sql_money(row.total_fee)
        avg_fee = (total_fee / Decimal(total_count)) if total_count else Decimal("0")
        return {
            "total_count": total_count,
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
            "zero_count": int(row.zero_count or 0),
            "total_fee": total_fee,
            "avg_fee": avg_fee,
        }

    def list_for_export(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        part_number: str | None,
        audit_status: str | None,
        only_zero: bool,
    ) -> list[StampingDieFee]:
        query = self._build_list_query(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=only_zero,
        )
        return (
            query.options(joinedload(StampingDieFee.items))
            .order_by(
                StampingDieFee.location.asc(),
                StampingDieFee.vehicle_model.asc(),
                StampingDieFee.id.asc(),
            )
            .all()
        )

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
        record = self.get_by_id(db, fee_id)
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
        location: str,
        vehicle_model: str,
    ) -> int:
        fee_ids = [
            row.id
            for row in (
                self._scope_query(db, year=year, location=location, vehicle_model=vehicle_model)
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
        count = self._scope_query(
            db, year=year, location=location, vehicle_model=vehicle_model
        ).delete(synchronize_session=False)
        db.flush()
        return count

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
    ) -> int:
        fee_ids = [
            row.id
            for row in (
                self._scope_query(db, year=year, location=location, vehicle_model=vehicle_model)
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
            self._scope_query(db, year=year, location=location, vehicle_model=vehicle_model)
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
        location: str,
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
            self._scope_query(db, year=year, location=location, vehicle_model=vehicle_model).filter(
                StampingDieFee.audit_status.in_([AUDIT_PENDING, AUDIT_REJECTED])
            ),
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
            self._scope_query(db, year=year, location=location, vehicle_model=vehicle_model).filter(
                StampingDieFee.audit_status == AUDIT_APPROVED
            ),
            values,
        )
        db.flush()
        return count

    def get_distinct_years(self, db: Session) -> list[int]:
        rows = db.query(StampingDieFee.year).distinct().order_by(StampingDieFee.year.desc()).all()
        return [row[0] for row in rows]
