"""焊接费写入：upsert、替换明细、按范围删未审、审核/反审。"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.bom import BomWeldingFee, BomWeldingFeeItem
from app.repositories.bom.welding_fee.queries import BomWeldingFeeQueries
from app.repositories.persist import apply_payload_fields, model_from_payload, query_update
from app.schemas.dto.bom_welding_fee_dto import (
    BomWeldingFeeItemPayload,
    BomWeldingFeeUpsertPayload,
    WeldingFeePatch,
)

logger = logging.getLogger("repository.bom.welding_fee")

_UPSERT_SKIP = frozenset({"id", "created_by", "created_at"})


class BomWeldingFeeWrites:
    def __init__(self, queries: BomWeldingFeeQueries | None = None) -> None:
        self._queries = queries or BomWeldingFeeQueries()

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
        existing = self._queries.get_by_business_key(
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
        record = self._queries.get_by_id(db, fee_id)
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

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        level: int | None = None,
        levels: list[int] | None = None,
    ) -> int:
        fee_ids = [
            row.id
            for row in (
                self._queries._scope_query(
                    db,
                    year=year,
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                    level=level,
                    levels=levels,
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
            self._queries._scope_query(
                db,
                year=year,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                level=level,
                levels=levels,
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
        levels: list[int] | None = None,
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
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                level=level,
                levels=levels,
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
        levels: list[int] | None = None,
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
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                level=level,
                levels=levels,
            ).filter(BomWeldingFee.audit_status == AUDIT_APPROVED),
            values,
        )
        db.flush()
        return int(count)
