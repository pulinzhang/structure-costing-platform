"""冲压零件价格核算结果 Repository。"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.stamping_part_cost import StampingPartCost


logger = logging.getLogger("repository.stamping_part_cost")


class StampingPartCostRepository:
    """零件价格核算结果数据访问。"""

    def get_by_id(self, db: Session, cost_id: int) -> Optional[StampingPartCost]:
        return (
            db.query(StampingPartCost)
            .filter(StampingPartCost.id == cost_id)
            .first()
        )

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
    ) -> Optional[StampingPartCost]:
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

    def upsert(self, db: Session, data: Dict[str, Any]) -> StampingPartCost:
        payload = dict(data)
        existing = self.get_by_business_key(
            db,
            year=payload["year"],
            month=payload["month"],
            location=payload["location"],
            stamping_supplier=payload["stamping_supplier"],
            vehicle_model=payload["vehicle_model"],
            version=payload["version"],
            part_number=payload["part_number"],
        )
        if existing:
            for key, value in payload.items():
                if key in ("created_by", "created_at"):
                    continue
                if hasattr(existing, key):
                    setattr(existing, key, value)
            db.flush()
            return existing

        if "audit_status" not in payload:
            payload = {**payload, "audit_status": AUDIT_PENDING}
        record = StampingPartCost(**payload)
        db.add(record)
        db.flush()
        return record

    def update_fields(
        self, db: Session, cost_id: int, update_data: Dict[str, Any]
    ) -> Optional[StampingPartCost]:
        record = self.get_by_id(db, cost_id)
        if not record:
            return None
        for key, value in update_data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        db.commit()
        db.refresh(record)
        return record

    def bulk_upsert(
        self, db: Session, data_list: List[Dict[str, Any]]
    ) -> List[StampingPartCost]:
        records = [self.upsert(db, data) for data in data_list]
        db.commit()
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
        stamping_supplier: str,
    ):
        return db.query(StampingPartCost).filter(
            StampingPartCost.year == year,
            StampingPartCost.month == month,
            StampingPartCost.location == location,
            StampingPartCost.stamping_supplier == stamping_supplier,
        )

    def _build_list_query(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        audit_status: Optional[str] = None,
    ):
        q = db.query(StampingPartCost)
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        if month is not None:
            q = q.filter(StampingPartCost.month == month)
        if location is not None:
            q = q.filter(StampingPartCost.location == location)
        if stamping_supplier is not None:
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
        year: Optional[int] = None,
        month: Optional[int] = None,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        audit_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[StampingPartCost], int]:
        q = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
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
        year: Optional[int] = None,
        month: Optional[int] = None,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        audit_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """按与列表相同的筛选条件汇总：均单价 / 待审 / 已审。"""
        q = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        row = q.with_entities(
            func.avg(StampingPartCost.unit_cost).label("avg_unit_cost"),
            func.sum(
                case((StampingPartCost.audit_status == AUDIT_PENDING, 1), else_=0)
            ).label("pending_count"),
            func.sum(
                case((StampingPartCost.audit_status == AUDIT_APPROVED, 1), else_=0)
            ).label("approved_count"),
        ).one()
        avg_value = row.avg_unit_cost
        return {
            "avg_unit_cost": float(avg_value) if avg_value is not None else None,
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
        }

    def list_for_export(
        self,
        db: Session,
        year: Optional[int] = None,
        month: Optional[int] = None,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        audit_status: Optional[str] = None,
    ) -> List[StampingPartCost]:
        q = db.query(StampingPartCost)
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        if month is not None:
            q = q.filter(StampingPartCost.month == month)
        if location is not None:
            q = q.filter(StampingPartCost.location == location)
        if stamping_supplier is not None:
            q = q.filter(StampingPartCost.stamping_supplier == stamping_supplier)
        if vehicle_model is not None:
            q = q.filter(StampingPartCost.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingPartCost.version == version)
        if part_number:
            q = q.filter(StampingPartCost.part_number.like(f"%{part_number}%"))
        if audit_status:
            q = q.filter(StampingPartCost.audit_status == audit_status)
        return (
            q.order_by(
                StampingPartCost.year.desc(),
                StampingPartCost.month.desc(),
                StampingPartCost.location,
                StampingPartCost.id.asc(),
            )
            .all()
        )

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str,
        statuses: List[str],
    ) -> int:
        return (
            self._scope_query(
                db,
                year=year,
                month=month,
                location=location,
                stamping_supplier=stamping_supplier,
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
        stamping_supplier: str,
    ) -> int:
        count = (
            self._scope_query(
                db,
                year=year,
                month=month,
                location=location,
                stamping_supplier=stamping_supplier,
            )
            .filter(StampingPartCost.audit_status != AUDIT_APPROVED)
            .delete(synchronize_session=False)
        )
        db.flush()
        logger.info(
            "批量删除未审核零件价格核算: year=%s month=%s location=%s supplier=%s count=%s",
            year,
            month,
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
        month: int,
        location: str,
        stamping_supplier: str,
        audited_by: str,
        audited_at,
        audit_remark: Optional[str],
        updated_by: Optional[str] = None,
    ) -> int:
        values: Dict[Any, Any] = {
            StampingPartCost.audit_status: AUDIT_APPROVED,
            StampingPartCost.audited_by: audited_by,
            StampingPartCost.audited_at: audited_at,
            StampingPartCost.audit_remark: audit_remark,
        }
        if updated_by is not None:
            values[StampingPartCost.updated_by] = updated_by
        count = (
            self._scope_query(
                db,
                year=year,
                month=month,
                location=location,
                stamping_supplier=stamping_supplier,
            )
            .filter(
                StampingPartCost.audit_status.in_([AUDIT_PENDING, AUDIT_REJECTED])
            )
            .update(values, synchronize_session=False)
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
        stamping_supplier: str,
        reverse_audited_by: str,
        reverse_audited_at,
        reverse_audit_remark: str,
        updated_by: Optional[str] = None,
    ) -> int:
        values: Dict[Any, Any] = {
            StampingPartCost.audit_status: AUDIT_PENDING,
            StampingPartCost.reverse_audited_by: reverse_audited_by,
            StampingPartCost.reverse_audited_at: reverse_audited_at,
            StampingPartCost.reverse_audit_remark: reverse_audit_remark,
        }
        if updated_by is not None:
            values[StampingPartCost.updated_by] = updated_by
        count = (
            self._scope_query(
                db,
                year=year,
                month=month,
                location=location,
                stamping_supplier=stamping_supplier,
            )
            .filter(StampingPartCost.audit_status == AUDIT_APPROVED)
            .update(values, synchronize_session=False)
        )
        db.flush()
        return count

    def get_distinct_years(self, db: Session) -> List[int]:
        results = (
            db.query(StampingPartCost.year)
            .distinct()
            .order_by(StampingPartCost.year.desc())
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_months(
        self, db: Session, year: Optional[int] = None
    ) -> List[int]:
        q = db.query(StampingPartCost.month).distinct()
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        results = q.order_by(StampingPartCost.month.desc()).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_locations(
        self, db: Session, year: Optional[int] = None, month: Optional[int] = None
    ) -> List[str]:
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
        year: Optional[int] = None,
        month: Optional[int] = None,
        location: Optional[str] = None,
    ) -> List[str]:
        q = db.query(StampingPartCost.stamping_supplier).distinct()
        if year is not None:
            q = q.filter(StampingPartCost.year == year)
        if month is not None:
            q = q.filter(StampingPartCost.month == month)
        if location is not None:
            q = q.filter(StampingPartCost.location == location)
        results = q.order_by(StampingPartCost.stamping_supplier).all()
        return [r[0] for r in results if r[0]]
