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
from app.models.bom import BomWeldingFee, BomWeldingFeeItem
from app.repositories.persist import apply_payload_fields, model_from_payload, query_update
from app.schemas.dto.bom_welding_fee_dto import (
    BomWeldingFeeItemPayload,
    BomWeldingFeeUpsertPayload,
    WeldingFeePatch,
)

logger = logging.getLogger("repository.bom.welding_fee")

_UPSERT_SKIP = frozenset({"id", "created_by", "created_at"})


class WeldingFeeFilterSummary(TypedDict):
    """列表筛选汇总（全量，无分页）。"""

    total_count: int
    total_fee: Decimal
    pending_count: int
    approved_count: int
    partial_count: int
    failed_count: int
    missing_price_count: int


class BomWeldingFeeRepository:
    """焊接费结果数据访问"""

    def get_by_id(self, db: Session, fee_id: int) -> BomWeldingFee | None:
        return (
            db.query(BomWeldingFee)
            .options(joinedload(BomWeldingFee.items))
            .filter(BomWeldingFee.id == fee_id)
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
    ) -> BomWeldingFee | None:
        return (
            db.query(BomWeldingFee)
            .filter(
                BomWeldingFee.year == year,
                BomWeldingFee.location == location,
                BomWeldingFee.vehicle_model == vehicle_model,
                BomWeldingFee.bom_version == bom_version,
                BomWeldingFee.source_breakdown_node_id == source_breakdown_node_id,
            )
            .first()
        )

    def replace_items(
        self,
        db: Session,
        fee_id: int,
        items_data: list[BomWeldingFeeItemPayload],
    ) -> None:
        record = (
            db.query(BomWeldingFee)
            .options(joinedload(BomWeldingFee.items))
            .filter(BomWeldingFee.id == fee_id)
            .first()
        )
        if record is None:
            return
        record.items.clear()
        for item in items_data:
            record.items.append(model_from_payload(BomWeldingFeeItem, item))
        db.flush()

    def upsert(self, db: Session, data: BomWeldingFeeUpsertPayload) -> tuple[BomWeldingFee, bool]:
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

        record = model_from_payload(BomWeldingFee, data)
        if not record.audit_status:
            record.audit_status = AUDIT_PENDING
        db.add(record)
        db.flush()
        self.replace_items(db, record.id, data.items)
        return record, True

    def update_fields(
        self, db: Session, fee_id: int, update_data: WeldingFeePatch
    ) -> BomWeldingFee | None:
        record = self.get_by_id(db, fee_id)
        if not record:
            return None
        apply_payload_fields(record, update_data)
        db.flush()
        db.refresh(record)
        return record

    def bulk_upsert(
        self, db: Session, data_list: list[BomWeldingFeeUpsertPayload]
    ) -> tuple[list[BomWeldingFee], int, int]:
        """批量 upsert，返回 (records, created_count, updated_count)。"""
        records: list[BomWeldingFee] = []
        created_count = 0
        updated_count = 0
        for data in data_list:
            record, created = self.upsert(db, data)
            records.append(record)
            if created:
                created_count += 1
            else:
                updated_count += 1
        db.flush()
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
        level: int | None = None,
    ) -> Query[BomWeldingFee]:
        q = db.query(BomWeldingFee).filter(
            BomWeldingFee.year == year,
            BomWeldingFee.location == location,
            BomWeldingFee.vehicle_model == vehicle_model,
            BomWeldingFee.bom_version == bom_version,
        )
        if level is not None:
            q = q.filter(BomWeldingFee.level == level)
        return q

    def count_by_calc_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        level: int | None = None,
    ) -> int:
        return int(
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                level=level,
            ).count()
        )

    def list_by_calc_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        level: int | None = None,
    ) -> list[BomWeldingFee]:
        return (
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                level=level,
            )
            .order_by(BomWeldingFee.part_number, BomWeldingFee.id.asc())
            .all()
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
        level: int | None = None,
    ) -> Query[BomWeldingFee]:
        q = db.query(BomWeldingFee)
        if year is not None:
            q = q.filter(BomWeldingFee.year == year)
        if location is not None:
            q = q.filter(BomWeldingFee.location == location)
        if vehicle_model is not None:
            q = q.filter(BomWeldingFee.vehicle_model == vehicle_model)
        if bom_version is not None:
            q = q.filter(BomWeldingFee.bom_version == bom_version)
        if part_number:
            q = q.filter(BomWeldingFee.part_number.like(f"%{part_number}%"))
        if audit_status:
            q = q.filter(BomWeldingFee.audit_status == audit_status)
        if calc_status:
            q = q.filter(BomWeldingFee.calc_status == calc_status)
        if level is not None:
            q = q.filter(BomWeldingFee.level == level)
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
        level: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomWeldingFee], int]:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            level=level,
        )
        total = q.count()
        rows = (
            q.options(noload(BomWeldingFee.items))
            .order_by(BomWeldingFee.id.asc())
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
        level: int | None = None,
    ) -> list[BomWeldingFee]:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            level=level,
        )
        rows: list[BomWeldingFee] = (
            q.options(joinedload(BomWeldingFee.items)).order_by(BomWeldingFee.id.asc()).all()
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
        level: int | None = None,
    ) -> WeldingFeeFilterSummary:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
            level=level,
        )
        row = q.with_entities(
            func.count(BomWeldingFee.id).label("total_count"),
            func.coalesce(func.sum(BomWeldingFee.final_welding_fee), 0).label("total_fee"),
            func.sum(case((BomWeldingFee.audit_status == AUDIT_PENDING, 1), else_=0)).label(
                "pending_count"
            ),
            func.sum(case((BomWeldingFee.audit_status == AUDIT_APPROVED, 1), else_=0)).label(
                "approved_count"
            ),
            func.sum(case((BomWeldingFee.calc_status == "partial", 1), else_=0)).label(
                "partial_count"
            ),
            func.sum(case((BomWeldingFee.calc_status == "failed", 1), else_=0)).label(
                "failed_count"
            ),
            func.sum(BomWeldingFee.missing_price_count).label("missing_price_count"),
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
        level: int | None = None,
    ) -> int:
        return int(
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                level=level,
            )
            .filter(BomWeldingFee.audit_status.in_(statuses))
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
        level: int | None = None,
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
                    level=level,
                )
                .filter(BomWeldingFee.audit_status != AUDIT_APPROVED)
                .with_entities(BomWeldingFee.id)
                .all()
            )
        ]
        if fee_ids:
            (
                db.query(BomWeldingFeeItem)
                .filter(BomWeldingFeeItem.fee_id.in_(fee_ids))
                .delete(synchronize_session=False)
            )
        count = (
            self._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                level=level,
            )
            .filter(BomWeldingFee.audit_status != AUDIT_APPROVED)
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
        level: int | None = None,
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
                level=level,
            ).filter(BomWeldingFee.audit_status.in_([AUDIT_PENDING, AUDIT_REJECTED])),
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
        level: int | None = None,
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
                level=level,
            ).filter(BomWeldingFee.audit_status == AUDIT_APPROVED),
            values,
        )
        db.flush()
        return int(count)

    def get_distinct_years(self, db: Session) -> list[int]:
        results = db.query(BomWeldingFee.year).distinct().order_by(BomWeldingFee.year.desc()).all()
        return [r[0] for r in results]

    def get_distinct_locations(self, db: Session, year: int | None = None) -> list[str]:
        q = db.query(BomWeldingFee.location).distinct()
        if year is not None:
            q = q.filter(BomWeldingFee.year == year)
        results = q.order_by(BomWeldingFee.location).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_vehicle_models(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
    ) -> list[str]:
        q = db.query(BomWeldingFee.vehicle_model).distinct()
        if year is not None:
            q = q.filter(BomWeldingFee.year == year)
        if location is not None:
            q = q.filter(BomWeldingFee.location == location)
        results = q.order_by(BomWeldingFee.vehicle_model).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_bom_versions(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        q = db.query(BomWeldingFee.bom_version).distinct()
        if year is not None:
            q = q.filter(BomWeldingFee.year == year)
        if location is not None:
            q = q.filter(BomWeldingFee.location == location)
        if vehicle_model is not None:
            q = q.filter(BomWeldingFee.vehicle_model == vehicle_model)
        results = q.order_by(BomWeldingFee.bom_version).all()
        return [r[0] for r in results if r[0]]
