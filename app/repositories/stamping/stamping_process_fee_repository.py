"""
冲压加工费结果 Repository
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session, joinedload, noload

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.stamping_process_fee import StampingProcessFee
from app.models.stamping_process_fee_item import StampingProcessFeeItem


def _needs_manual_fix_clause():
    """最终加工费为空或为 0：算费失败 / 零价且尚未补价。"""
    return or_(
        StampingProcessFee.final_processing_fee.is_(None),
        StampingProcessFee.final_processing_fee == 0,
    )


logger = logging.getLogger("repository.stamping")

# upsert 行内携带的工序分项键（非主表列）
PROCESS_ITEMS_KEY = "_process_items"


class StampingProcessFeeRepository:
    """冲压加工费结果数据访问"""

    def get_by_id(self, db: Session, fee_id: int) -> Optional[StampingProcessFee]:
        return (
            db.query(StampingProcessFee)
            .options(joinedload(StampingProcessFee.process_items))
            .filter(StampingProcessFee.id == fee_id)
            .first()
        )

    def list_by_ids(self, db: Session, fee_ids: list[int]) -> list[StampingProcessFee]:
        """按主键批量查询（含工序分项，供导出溯源）。"""
        if not fee_ids:
            return []
        return (
            db.query(StampingProcessFee)
            .options(joinedload(StampingProcessFee.process_items))
            .filter(StampingProcessFee.id.in_(fee_ids))
            .all()
        )

    def replace_items(
        self,
        db: Session,
        fee_id: int,
        items_data: List[Dict[str, Any]],
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
            record.process_items.append(StampingProcessFeeItem(**item))
        db.flush()

    def get_by_business_key(
        self,
        db: Session,
        year: int,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
        part_number: str,
    ) -> Optional[StampingProcessFee]:
        q = db.query(StampingProcessFee).filter(
            StampingProcessFee.year == year,
            StampingProcessFee.location == location,
            StampingProcessFee.stamping_supplier == stamping_supplier,
            StampingProcessFee.vehicle_model == vehicle_model,
            StampingProcessFee.version == version,
            StampingProcessFee.part_number == part_number,
        )
        return q.first()

    def upsert(self, db: Session, data: Dict[str, Any]) -> StampingProcessFee:
        payload = dict(data)
        items_data = payload.pop(PROCESS_ITEMS_KEY, None)

        existing = self.get_by_business_key(
            db,
            year=payload["year"],
            location=payload["location"],
            stamping_supplier=payload.get("stamping_supplier"),
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
            if items_data is not None:
                self.replace_items(db, existing.id, items_data)
            return existing

        if "audit_status" not in payload:
            payload = {**payload, "audit_status": AUDIT_PENDING}
        record = StampingProcessFee(**payload)
        db.add(record)
        db.flush()
        if items_data is not None:
            self.replace_items(db, record.id, items_data)
        return record

    def update_fields(
        self, db: Session, fee_id: int, update_data: Dict[str, Any]
    ) -> Optional[StampingProcessFee]:
        record = self.get_by_id(db, fee_id)
        if not record:
            return None
        for key, value in update_data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        db.commit()
        db.refresh(record)
        return record

    def bulk_upsert(self, db: Session, data_list: List[Dict[str, Any]]) -> List[StampingProcessFee]:
        records = [self.upsert(db, data) for data in data_list]
        db.commit()
        for record in records:
            db.refresh(record)
        logger.info("批量 upsert 冲压加工费: %s 条", len(records))
        return records

    def _scope_query(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        stamping_supplier: str,
    ):
        return db.query(StampingProcessFee).filter(
            StampingProcessFee.year == year,
            StampingProcessFee.location == location,
            StampingProcessFee.stamping_supplier == stamping_supplier,
        )

    def _build_list_query(
        self,
        db: Session,
        year: Optional[int] = None,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        audit_status: Optional[str] = None,
        only_zero: bool = False,
    ):
        q = db.query(StampingProcessFee)
        if year is not None:
            q = q.filter(StampingProcessFee.year == year)
        if location is not None:
            q = q.filter(StampingProcessFee.location == location)
        if stamping_supplier is not None:
            q = q.filter(StampingProcessFee.stamping_supplier == stamping_supplier)
        if vehicle_model is not None:
            q = q.filter(StampingProcessFee.vehicle_model == vehicle_model)
        if version is not None:
            q = q.filter(StampingProcessFee.version == version)
        if part_number:
            q = q.filter(StampingProcessFee.part_number.like(f"%{part_number}%"))
        if audit_status:
            q = q.filter(StampingProcessFee.audit_status == audit_status)
        if only_zero:
            q = q.filter(_needs_manual_fix_clause())
        return q

    def paginate(
        self,
        db: Session,
        year: Optional[int] = None,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        audit_status: Optional[str] = None,
        only_zero: bool = False,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[StampingProcessFee], int]:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=only_zero,
        )
        total = q.count()
        rows = (
            q.options(noload(StampingProcessFee.process_items))
            .order_by(
                StampingProcessFee.year.desc(),
                StampingProcessFee.location,
                StampingProcessFee.stamping_supplier,
                StampingProcessFee.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def summarize_by_filters(
        self,
        db: Session,
        year: Optional[int] = None,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        audit_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """按筛选条件汇总：总金额 / 件均 / 待补价 / 待审 / 已审 / 版本标签。"""
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=False,
        )
        row = q.with_entities(
            func.count(StampingProcessFee.id).label("total_count"),
            func.coalesce(func.sum(StampingProcessFee.final_processing_fee), 0).label(
                "total_fee"
            ),
            func.avg(StampingProcessFee.final_processing_fee).label("avg_fee"),
            func.sum(
                case((_needs_manual_fix_clause(), 1), else_=0)
            ).label("zero_count"),
            func.sum(
                case((StampingProcessFee.audit_status == AUDIT_PENDING, 1), else_=0)
            ).label("pending_count"),
            func.sum(
                case(
                    (StampingProcessFee.audit_status == AUDIT_APPROVED, 1),
                    else_=0,
                )
            ).label("approved_count"),
        ).one()

        avg_value = row.avg_fee

        version_q = self._build_list_query(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=False,
        )
        version_rows = (
            version_q.with_entities(StampingProcessFee.version)
            .distinct()
            .order_by(StampingProcessFee.version.asc())
            .all()
        )
        versions = [r[0] for r in version_rows if r[0]]
        if version:
            version_label = version
        elif len(versions) == 0:
            version_label = "—"
        elif len(versions) == 1:
            version_label = versions[0]
        else:
            version_label = f"{len(versions)} 个版本"

        return {
            "total_count": int(row.total_count or 0),
            "total_fee": float(row.total_fee or 0),
            "avg_fee": float(avg_value) if avg_value is not None else None,
            "zero_count": int(row.zero_count or 0),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
            "version_label": version_label,
        }

    def list_for_export(
        self,
        db: Session,
        year: Optional[int] = None,
        location: Optional[str] = None,
        stamping_supplier: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        version: Optional[str] = None,
        part_number: Optional[str] = None,
        audit_status: Optional[str] = None,
    ) -> List[StampingProcessFee]:
        q = self._build_list_query(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )
        return (
            q.options(joinedload(StampingProcessFee.process_items))
            .order_by(
                StampingProcessFee.year.desc(),
                StampingProcessFee.location,
                StampingProcessFee.stamping_supplier,
                StampingProcessFee.id.asc(),
            )
            .all()
        )

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        stamping_supplier: str,
        statuses: List[str],
    ) -> int:
        return (
            self._scope_query(
                db,
                year=year,
                location=location,
                stamping_supplier=stamping_supplier,
            )
            .filter(StampingProcessFee.audit_status.in_(statuses))
            .count()
        )

    def delete_unaudited_by_scope(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        stamping_supplier: str,
    ) -> int:
        fee_ids = [
            row.id
            for row in (
                self._scope_query(
                    db,
                    year=year,
                    location=location,
                    stamping_supplier=stamping_supplier,
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
            self._scope_query(
                db,
                year=year,
                location=location,
                stamping_supplier=stamping_supplier,
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
        stamping_supplier: str,
        audited_by: str,
        audited_at,
        audit_remark: Optional[str],
        updated_by: Optional[str] = None,
    ) -> int:
        values: Dict[Any, Any] = {
            StampingProcessFee.audit_status: AUDIT_APPROVED,
            StampingProcessFee.audited_by: audited_by,
            StampingProcessFee.audited_at: audited_at,
            StampingProcessFee.audit_remark: audit_remark,
        }
        if updated_by is not None:
            values[StampingProcessFee.updated_by] = updated_by
        count = (
            self._scope_query(
                db,
                year=year,
                location=location,
                stamping_supplier=stamping_supplier,
            )
            .filter(
                StampingProcessFee.audit_status.in_([AUDIT_PENDING, AUDIT_REJECTED])
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
        location: str,
        stamping_supplier: str,
        reverse_audited_by: str,
        reverse_audited_at,
        reverse_audit_remark: str,
        updated_by: Optional[str] = None,
    ) -> int:
        values: Dict[Any, Any] = {
            StampingProcessFee.audit_status: AUDIT_PENDING,
            StampingProcessFee.reverse_audited_by: reverse_audited_by,
            StampingProcessFee.reverse_audited_at: reverse_audited_at,
            StampingProcessFee.reverse_audit_remark: reverse_audit_remark,
        }
        if updated_by is not None:
            values[StampingProcessFee.updated_by] = updated_by
        count = (
            self._scope_query(
                db,
                year=year,
                location=location,
                stamping_supplier=stamping_supplier,
            )
            .filter(StampingProcessFee.audit_status == AUDIT_APPROVED)
            .update(values, synchronize_session=False)
        )
        db.flush()
        return count

    def get_distinct_years(self, db: Session) -> List[int]:
        results = (
            db.query(StampingProcessFee.year)
            .distinct()
            .order_by(StampingProcessFee.year.desc())
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_locations(self, db: Session, year: Optional[int] = None) -> List[str]:
        q = db.query(StampingProcessFee.location).distinct()
        if year is not None:
            q = q.filter(StampingProcessFee.year == year)
        results = q.order_by(StampingProcessFee.location).all()
        return [r[0] for r in results if r[0]]

    def get_distinct_suppliers(
        self,
        db: Session,
        year: Optional[int] = None,
        location: Optional[str] = None,
    ) -> List[str]:
        q = db.query(StampingProcessFee.stamping_supplier).distinct()
        if year is not None:
            q = q.filter(StampingProcessFee.year == year)
        if location is not None:
            q = q.filter(StampingProcessFee.location == location)
        results = q.order_by(StampingProcessFee.stamping_supplier).all()
        return [r[0] for r in results if r[0]]
