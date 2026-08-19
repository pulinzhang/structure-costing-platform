"""
BOM 焊接费结果 Repository
"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import case, func
from sqlalchemy.orm import Query, Session, joinedload, noload

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.bom import BomL0WeldingFee, BomL0WeldingFeeItem
from app.repositories.persist import apply_payload_fields, model_from_payload, query_update
from app.schemas.dto.bom_l0_welding_fee_dto import (
    BomL0WeldingFeeItemPayload,
    BomL0WeldingFeeUpsertPayload,
    L0WeldingFeePatch,
)

logger = logging.getLogger("repository.bom.l0_welding_fee")

_UPSERT_SKIP = frozenset({"id", "created_by", "created_at"})


class L0WeldingFeeFilterSummary(TypedDict):
    """列表筛选汇总。"""

    total_count: int
    total_fee: Decimal
    pending_count: int
    approved_count: int
    partial_count: int
    failed_count: int
    missing_price_count: int


class L0WeldingFeeListFilters(TypedDict):
    """成品焊接费列表筛选体。"""

    year: int | None
    location: str | None
    vehicle_model: str | None
    bom_version: str | None
    part_number: str | None
    audit_status: str | None
    calc_status: str | None
    summary: L0WeldingFeeFilterSummary


class BomL0WeldingFeeRepository:
    """焊接费结果数据访问"""

    def get_by_id(self, db: Session, fee_id: int) -> BomL0WeldingFee | None:
        return (
            db.query(BomL0WeldingFee)
            .options(joinedload(BomL0WeldingFee.items))
            .filter(BomL0WeldingFee.id == fee_id)
            .first()
        )

    def get_by_business_key(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        source_breakdown_node_id: int | None,
    ) -> BomL0WeldingFee | None:
        return (
            db.query(BomL0WeldingFee)
            .filter(
                BomL0WeldingFee.year == year,
                BomL0WeldingFee.location == location,
                BomL0WeldingFee.vehicle_model == vehicle_model,
                BomL0WeldingFee.bom_version == bom_version,
                BomL0WeldingFee.source_breakdown_node_id == source_breakdown_node_id,
            )
            .first()
        )

    def replace_items(
        self,
        db: Session,
        fee_id: int,
        items_data: list[BomL0WeldingFeeItemPayload],
    ) -> None:
        record = (
            db.query(BomL0WeldingFee)
            .options(joinedload(BomL0WeldingFee.items))
            .filter(BomL0WeldingFee.id == fee_id)
            .first()
        )
        if record is None:
            return
        record.items.clear()
        for item in items_data:
            record.items.append(model_from_payload(BomL0WeldingFeeItem, item))
        db.flush()

    def upsert(
        self, db: Session, data: BomL0WeldingFeeUpsertPayload
    ) -> tuple[BomL0WeldingFee, bool]:
        """返回 (record, created)。"""
        existing = self.get_by_business_key(
            db,
            year=data.year,
            location=data.location,
            vehicle_model=data.vehicle_model,
            bom_version=data.bom_version,
            source_breakdown_node_id=data.source_breakdown_node_id,
        )
        if existing:
            apply_payload_fields(existing, data, skip=_UPSERT_SKIP)
            db.flush()
            self.replace_items(db, existing.id, data.items)
            return existing, False

        record = model_from_payload(BomL0WeldingFee, data)
        if not record.audit_status:
            record.audit_status = AUDIT_PENDING
        db.add(record)
        db.flush()
        self.replace_items(db, record.id, data.items)
        return record, True

    def update_fields(
        self, db: Session, fee_id: int, update_data: L0WeldingFeePatch
    ) -> BomL0WeldingFee | None:
        record = self.get_by_id(db, fee_id)
        if not record:
            return None
        apply_payload_fields(record, update_data)
        db.commit()
        db.refresh(record)
        return record

    def bulk_upsert(
        self, db: Session, data_list: list[BomL0WeldingFeeUpsertPayload]
    ) -> tuple[list[BomL0WeldingFee], int, int]:
        """批量 upsert，返回 (records, created_count, updated_count)。"""
        records: list[BomL0WeldingFee] = []
        created_count = 0
        updated_count = 0
        for data in data_list:
            record, created = self.upsert(db, data)
            records.append(record)
            if created:
                created_count += 1
            else:
                updated_count += 1
        db.commit()
        for record in records:
            db.refresh(record)
        logger.info(
            "批量 upsert 焊接费: %s 条 (new=%s update=%s)",
            len(records),
            created_count,
            updated_count,
        )
        return records, created_count, updated_count

    def _scope_query(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> Query[BomL0WeldingFee]:
        return db.query(BomL0WeldingFee).filter(
            BomL0WeldingFee.year == year,
            BomL0WeldingFee.location == location,
            BomL0WeldingFee.vehicle_model == vehicle_model,
            BomL0WeldingFee.bom_version == bom_version,
        )

    def _build_list_query(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
    ) -> Query[BomL0WeldingFee]:
        q = db.query(BomL0WeldingFee)
        if year is not None:
            q = q.filter(BomL0WeldingFee.year == year)
        if location is not None:
            q = q.filter(BomL0WeldingFee.location == location)
        if vehicle_model is not None:
            q = q.filter(BomL0WeldingFee.vehicle_model == vehicle_model)
        if bom_version is not None:
            q = q.filter(BomL0WeldingFee.bom_version == bom_version)
        if part_number:
            q = q.filter(BomL0WeldingFee.part_number.like(f"%{part_number}%"))
        if audit_status:
            q = q.filter(BomL0WeldingFee.audit_status == audit_status)
        if calc_status:
            q = q.filter(BomL0WeldingFee.calc_status == calc_status)
        return q

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomL0WeldingFee], int]:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
        )
        total = q.count()
        rows = (
            q.options(noload(BomL0WeldingFee.items))
            .order_by(
                BomL0WeldingFee.year.desc(),
                BomL0WeldingFee.location,
                BomL0WeldingFee.vehicle_model,
                BomL0WeldingFee.bom_version,
                BomL0WeldingFee.part_number,
                BomL0WeldingFee.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
    ) -> list[BomL0WeldingFee]:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
        )
        rows: list[BomL0WeldingFee] = (
            q.options(joinedload(BomL0WeldingFee.items))
            .order_by(
                BomL0WeldingFee.year.desc(),
                BomL0WeldingFee.location,
                BomL0WeldingFee.vehicle_model,
                BomL0WeldingFee.bom_version,
                BomL0WeldingFee.part_number,
                BomL0WeldingFee.id.asc(),
            )
            .all()
        )
        return rows

    def summarize_by_filters(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
    ) -> L0WeldingFeeFilterSummary:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
        )
        row = q.with_entities(
            func.count(BomL0WeldingFee.id).label("total_count"),
            func.coalesce(func.sum(BomL0WeldingFee.final_l0_welding_fee), 0).label("total_fee"),
            func.sum(
                case((BomL0WeldingFee.audit_status == AUDIT_PENDING, 1), else_=0)
            ).label("pending_count"),
            func.sum(
                case((BomL0WeldingFee.audit_status == AUDIT_APPROVED, 1), else_=0)
            ).label("approved_count"),
            func.sum(
                case((BomL0WeldingFee.calc_status == "partial", 1), else_=0)
            ).label("partial_count"),
            func.sum(
                case((BomL0WeldingFee.calc_status == "failed", 1), else_=0)
            ).label("failed_count"),
            func.sum(BomL0WeldingFee.missing_price_count).label("missing_price_count"),
        ).one()

        return {
            "total_count": int(row.total_count or 0),
            "total_fee": Decimal(str(row.total_fee or 0)),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
            "partial_count": int(row.partial_count or 0),
            "failed_count": int(row.failed_count or 0),
            "missing_price_count": int(row.missing_price_count or 0),
        }

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        statuses: list[str],
    ) -> int:
        return int(
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
            )
            .filter(BomL0WeldingFee.audit_status.in_(statuses))
            .count()
        )

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> int:
        fee_ids = [
            row.id
            for row in (
                self._scope_query(
                    db,
                    year=year,
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                )
                .filter(BomL0WeldingFee.audit_status != AUDIT_APPROVED)
                .with_entities(BomL0WeldingFee.id)
                .all()
            )
        ]
        if fee_ids:
            (
                db.query(BomL0WeldingFeeItem)
                .filter(BomL0WeldingFeeItem.fee_id.in_(fee_ids))
                .delete(synchronize_session=False)
            )
        count = (
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
            )
            .filter(BomL0WeldingFee.audit_status != AUDIT_APPROVED)
            .delete(synchronize_session=False)
        )
        db.flush()
        logger.info(
            "批量删除未审核焊接费: year=%s location=%s vehicle=%s version=%s count=%s",
            year,
            location,
            vehicle_model,
            bom_version,
            count,
        )
        return int(count)

    def approve_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
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
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
            ).filter(
                BomL0WeldingFee.audit_status.in_([AUDIT_PENDING, AUDIT_REJECTED])
            ),
            values,
        )
        db.flush()
        return int(count)

    def reverse_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
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
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
            ).filter(BomL0WeldingFee.audit_status == AUDIT_APPROVED),
            values,
        )
        db.flush()
        return int(count)

    def get_distinct_years(self, db: Session) -> list[int]:
        results = (
            db.query(BomL0WeldingFee.year)
            .distinct()
            .order_by(BomL0WeldingFee.year.desc())
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_locations(self, db: Session, year: int | None = None) -> list[str]:
        q = db.query(BomL0WeldingFee.location).distinct()
        if year is not None:
            q = q.filter(BomL0WeldingFee.year == year)
        results = q.order_by(BomL0WeldingFee.location).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_vehicle_models(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
    ) -> list[str]:
        q = db.query(BomL0WeldingFee.vehicle_model).distinct()
        if year is not None:
            q = q.filter(BomL0WeldingFee.year == year)
        if location is not None:
            q = q.filter(BomL0WeldingFee.location == location)
        results = q.order_by(BomL0WeldingFee.vehicle_model).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_bom_versions(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        q = db.query(BomL0WeldingFee.bom_version).distinct()
        if year is not None:
            q = q.filter(BomL0WeldingFee.year == year)
        if location is not None:
            q = q.filter(BomL0WeldingFee.location == location)
        if vehicle_model is not None:
            q = q.filter(BomL0WeldingFee.vehicle_model == vehicle_model)
        results = q.order_by(BomL0WeldingFee.bom_version).all()
        return [r[0] for r in results if r[0]]
