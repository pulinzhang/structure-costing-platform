"""冲压零件价格核算结果 Repository。"""

import logging
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import case, false, func
from sqlalchemy.orm import Query, Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.costing import StampingPartCost
from app.repositories.persist import apply_payload_fields, model_from_payload, query_update
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostPatch,
    StampingPartCostUpsertPayload,
)


class PartCostFilterSummary(TypedDict):
    """列表筛选汇总：均单价 / 待审 / 已审。"""

    avg_unit_cost: Decimal | None
    pending_count: int
    approved_count: int


class PartCostListFilters(TypedDict):
    """零件核价列表筛选体。"""

    years: list[int]
    months: list[int]
    locations: list[str]
    suppliers: list[str]
    vehicle_models: list[str]
    versions: list[str]
    summary: PartCostFilterSummary


logger = logging.getLogger("repository.stamping_part_cost")

_UPSERT_SKIP = frozenset({"id", "created_by", "created_at"})


class StampingPartCostRepository:
    """零件价格核算结果数据访问。"""

    def get_by_id(self, db: Session, cost_id: int) -> StampingPartCost | None:
        return db.query(StampingPartCost).filter(StampingPartCost.id == cost_id).first()

    def get_by_business_key(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
        part_number: str,
    ) -> StampingPartCost | None:
        return (
            db.query(StampingPartCost)
            .filter(
                StampingPartCost.year == year,
                StampingPartCost.month == month,
                StampingPartCost.location == location,
                StampingPartCost.stamping_supplier == stamping_supplier,
                StampingPartCost.vehicle_model == vehicle_model,
                StampingPartCost.version == version,
                StampingPartCost.part_number == part_number,
            )
            .first()
        )

    def upsert(self, db: Session, data: StampingPartCostUpsertPayload) -> StampingPartCost:
        existing = self.get_by_business_key(
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
        record = self.get_by_id(db, cost_id)
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

    def _scope_query(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> Query[StampingPartCost]:
        return self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
        )

    def _build_list_query(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> Query[StampingPartCost]:
        q = db.query(StampingPartCost)
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        if month is not None:
            q = q.filter(StampingPartCost.month == month)
        if locations is not None:
            q = q.filter(StampingPartCost.location.in_(locations))
        elif location is not None:
            q = q.filter(StampingPartCost.location == location)
        if stamping_suppliers is not None:
            if not stamping_suppliers:
                q = q.filter(false())
            else:
                q = q.filter(StampingPartCost.stamping_supplier.in_(stamping_suppliers))
        elif stamping_supplier is not None:
            q = q.filter(StampingPartCost.stamping_supplier == stamping_supplier)
        if vehicle_model is not None:
            q = q.filter(StampingPartCost.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPartCost.version == version)
        if part_number:
            q = q.filter(StampingPartCost.part_number.like(f"%{part_number}%"))
        if audit_status:
            q = q.filter(StampingPartCost.audit_status == audit_status)
        return q

    def paginate(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StampingPartCost], int]:
        q = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        total = q.count()
        rows = (
            q.order_by(
                StampingPartCost.year.desc(),
                StampingPartCost.month.desc(),
                StampingPartCost.location,
                StampingPartCost.stamping_supplier,
                StampingPartCost.id.asc(),
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
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> PartCostFilterSummary:
        """按与列表相同的筛选条件汇总：均单价 / 待审 / 已审。"""
        q = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        row = q.with_entities(
            func.avg(StampingPartCost.unit_cost).label("avg_unit_cost"),
            func.sum(case((StampingPartCost.audit_status == AUDIT_PENDING, 1), else_=0)).label(
                "pending_count"
            ),
            func.sum(case((StampingPartCost.audit_status == AUDIT_APPROVED, 1), else_=0)).label(
                "approved_count"
            ),
        ).one()
        avg_value = row.avg_unit_cost
        return {
            "avg_unit_cost": (Decimal(str(avg_value)) if avg_value is not None else None),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
        }

    def list_for_export(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        stamping_supplier: str | None = None,
        stamping_suppliers: Sequence[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> list[StampingPartCost]:
        q = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            stamping_supplier=stamping_supplier,
            stamping_suppliers=stamping_suppliers,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        return q.order_by(
            StampingPartCost.year.desc(),
            StampingPartCost.month.desc(),
            StampingPartCost.location,
            StampingPartCost.id.asc(),
        ).all()

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        statuses: list[str],
    ) -> int:
        return (
            self._scope_query(
                db,
                year=year,
                month=month,
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
                version=version,
            )
            .filter(StampingPartCost.audit_status.in_(statuses))
            .count()
        )

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
            self._scope_query(
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
            self._scope_query(
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
            self._scope_query(
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

    def get_distinct_years(self, db: Session) -> list[int]:
        results = (
            db.query(StampingPartCost.year).distinct().order_by(StampingPartCost.year.desc()).all()
        )
        return [r[0] for r in results]

    def get_distinct_months(self, db: Session, year: int | None = None) -> list[int]:
        q = db.query(StampingPartCost.month).distinct()
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        results = q.order_by(StampingPartCost.month.desc()).all()
        return [r[0] for r in results if r[0]]

    def count_calc_success_with_unit_cost(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
    ) -> int:
        return (
            db.query(StampingPartCost)
            .filter(
                StampingPartCost.location == location,
                StampingPartCost.vehicle_model == vehicle_model,
                StampingPartCost.year == year,
                StampingPartCost.month == month,
                StampingPartCost.calc_status == "success",
                StampingPartCost.unit_cost.isnot(None),
            )
            .count()
        )

    def list_calc_success_with_unit_cost(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
    ) -> list[StampingPartCost]:
        return (
            db.query(StampingPartCost)
            .filter(
                StampingPartCost.location == location,
                StampingPartCost.vehicle_model == vehicle_model,
                StampingPartCost.year == year,
                StampingPartCost.month == month,
                StampingPartCost.calc_status == "success",
                StampingPartCost.unit_cost.isnot(None),
            )
            .order_by(StampingPartCost.part_number, StampingPartCost.id.asc())
            .all()
        )

    def list_success_by_part_numbers(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        part_numbers: list[str],
    ) -> list[StampingPartCost]:
        if not part_numbers:
            return []
        unique = list(dict.fromkeys(part_numbers))
        rows: list[StampingPartCost] = []
        for offset in range(0, len(unique), 400):
            chunk = unique[offset : offset + 400]
            rows.extend(
                db.query(StampingPartCost)
                .filter(
                    StampingPartCost.location == location,
                    StampingPartCost.vehicle_model == vehicle_model,
                    StampingPartCost.year == year,
                    StampingPartCost.month == month,
                    StampingPartCost.part_number.in_(chunk),
                    StampingPartCost.calc_status == "success",
                    StampingPartCost.unit_cost.isnot(None),
                )
                .order_by(StampingPartCost.part_number, StampingPartCost.id.asc())
                .all()
            )
        return rows

    def get_distinct_locations(
        self, db: Session, year: int | None = None, month: int | None = None
    ) -> list[str]:
        q = db.query(StampingPartCost.location).distinct()
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        if month is not None:
            q = q.filter(StampingPartCost.month == month)
        results = q.order_by(StampingPartCost.location).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_suppliers(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> list[str]:
        q = db.query(StampingPartCost.stamping_supplier).distinct()
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        if month is not None:
            q = q.filter(StampingPartCost.month == month)
        if locations is not None:
            q = q.filter(StampingPartCost.location.in_(locations))
        elif location is not None:
            q = q.filter(StampingPartCost.location == location)
        if vehicle_model is not None:
            q = q.filter(StampingPartCost.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPartCost.version == version)
        results = q.order_by(StampingPartCost.stamping_supplier).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_versions(
        self,
        db: Session,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        vehicle_model: str | None = None,
        stamping_supplier: str | None = None,
    ) -> list[str]:
        q = db.query(StampingPartCost.version).distinct()
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        if month is not None:
            q = q.filter(StampingPartCost.month == month)
        if locations is not None:
            q = q.filter(StampingPartCost.location.in_(locations))
        elif location is not None:
            q = q.filter(StampingPartCost.location == location)
        if vehicle_model is not None:
            q = q.filter(StampingPartCost.vehicle_model == vehicle_model)
        if stamping_supplier is not None:
            q = q.filter(StampingPartCost.stamping_supplier == stamping_supplier)
        results = q.order_by(StampingPartCost.version).all()
        return [r[0] for r in results if r[0]]
