"""
焊接工费单价 Repository
数据访问层，只负责与数据库交互
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.bom_welding_unit_price import BomWeldingUnitPrice

logger = logging.getLogger("repository.bom")


class BomWeldingUnitPriceRepository:
    """焊接工费单价数据访问"""

    def get_by_id(self, db: Session, id: int) -> Optional[BomWeldingUnitPrice]:
        return db.query(BomWeldingUnitPrice).filter(BomWeldingUnitPrice.id == id).first()

    def get_by_location_year_item(
        self, db: Session, location: str, year: int, item_name: str
    ) -> Optional[BomWeldingUnitPrice]:
        return (
            db.query(BomWeldingUnitPrice)
            .filter(
                and_(
                    BomWeldingUnitPrice.location == location,
                    BomWeldingUnitPrice.year == year,
                    BomWeldingUnitPrice.item_name == item_name,
                )
            )
            .first()
        )

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> List[BomWeldingUnitPrice]:
        return (
            db.query(BomWeldingUnitPrice)
            .filter(
                and_(
                    BomWeldingUnitPrice.location == location,
                    BomWeldingUnitPrice.year == year,
                )
            )
            .order_by(BomWeldingUnitPrice.item_name)
            .all()
        )

    def list_by_year(self, db: Session, year: int) -> List[BomWeldingUnitPrice]:
        return (
            db.query(BomWeldingUnitPrice)
            .filter(BomWeldingUnitPrice.year == year)
            .order_by(BomWeldingUnitPrice.location, BomWeldingUnitPrice.item_name)
            .all()
        )

    def _build_list_query(
        self,
        db: Session,
        location: Optional[str] = None,
        year: Optional[int] = None,
        audit_status: Optional[str] = None,
    ):
        q = db.query(BomWeldingUnitPrice)
        if location is not None:
            q = q.filter(BomWeldingUnitPrice.location == location)
        if year is not None:
            q = q.filter(BomWeldingUnitPrice.year == year)
        if audit_status:
            q = q.filter(BomWeldingUnitPrice.audit_status == audit_status)
        return q

    def paginate(
        self,
        db: Session,
        location: Optional[str] = None,
        year: Optional[int] = None,
        audit_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[BomWeldingUnitPrice], int]:
        q = self._build_list_query(
            db, location=location, year=year, audit_status=audit_status
        )
        total = q.count()
        records = (
            q.order_by(
                BomWeldingUnitPrice.location,
                BomWeldingUnitPrice.year,
                BomWeldingUnitPrice.item_name,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total

    def summarize_by_filters(
        self,
        db: Session,
        location: Optional[str] = None,
        year: Optional[int] = None,
        audit_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        q = self._build_list_query(
            db, location=location, year=year, audit_status=audit_status
        )
        row = q.with_entities(
            func.count(BomWeldingUnitPrice.id).label("total_count"),
            func.sum(
                case((BomWeldingUnitPrice.audit_status == AUDIT_PENDING, 1), else_=0)
            ).label("pending_count"),
            func.sum(
                case((BomWeldingUnitPrice.audit_status == AUDIT_APPROVED, 1), else_=0)
            ).label("approved_count"),
        ).one()
        return {
            "total_count": int(row.total_count or 0),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
        }

    def list_for_export(
        self,
        db: Session,
        location: Optional[str] = None,
        year: Optional[int] = None,
        audit_status: Optional[str] = None,
    ) -> List[BomWeldingUnitPrice]:
        q = self._build_list_query(
            db, location=location, year=year, audit_status=audit_status
        )
        return (
            q.order_by(
                BomWeldingUnitPrice.location,
                BomWeldingUnitPrice.year,
                BomWeldingUnitPrice.item_name,
            )
            .all()
        )

    def list_all(self, db: Session) -> List[BomWeldingUnitPrice]:
        return (
            db.query(BomWeldingUnitPrice)
            .order_by(
                BomWeldingUnitPrice.location,
                BomWeldingUnitPrice.year,
                BomWeldingUnitPrice.item_name,
            )
            .all()
        )

    def get_distinct_locations(self, db: Session) -> List[str]:
        results = (
            db.query(BomWeldingUnitPrice.location)
            .distinct()
            .order_by(BomWeldingUnitPrice.location)
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_years(self, db: Session) -> List[int]:
        results = (
            db.query(BomWeldingUnitPrice.year)
            .distinct()
            .order_by(BomWeldingUnitPrice.year.desc())
            .all()
        )
        return [r[0] for r in results]

    def count_by_location_year_and_statuses(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        statuses: List[str],
    ) -> int:
        return (
            db.query(BomWeldingUnitPrice)
            .filter(
                BomWeldingUnitPrice.location == location,
                BomWeldingUnitPrice.year == year,
                BomWeldingUnitPrice.audit_status.in_(statuses),
            )
            .count()
        )

    def create(
        self, db: Session, data: Dict[str, Any], *, commit: bool = True
    ) -> BomWeldingUnitPrice:
        payload = dict(data)
        if "audit_status" not in payload:
            payload["audit_status"] = AUDIT_PENDING
        record = BomWeldingUnitPrice(**payload)
        db.add(record)
        if commit:
            db.commit()
        else:
            db.flush()
        db.refresh(record)
        logger.info(
            "创建焊接工费单价: location=%s, year=%s, item=%s, id=%s",
            payload.get("location"),
            payload.get("year"),
            payload.get("item_name"),
            record.id,
        )
        return record

    def update(
        self,
        db: Session,
        id: int,
        update_data: Dict[str, Any],
        *,
        commit: bool = True,
    ) -> Optional[BomWeldingUnitPrice]:
        record = self.get_by_id(db, id)
        if not record:
            return None
        for key, value in update_data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        if commit:
            db.commit()
        else:
            db.flush()
        db.refresh(record)
        logger.info("更新焊接工费单价: id=%s", id)
        return record

    def delete(self, db: Session, id: int) -> bool:
        record = self.get_by_id(db, id)
        if not record:
            return False
        db.delete(record)
        db.commit()
        logger.info("删除焊接工费单价: id=%s", id)
        return True

    def delete_by_location_year(self, db: Session, location: str, year: int) -> int:
        count = (
            db.query(BomWeldingUnitPrice)
            .filter(
                and_(
                    BomWeldingUnitPrice.location == location,
                    BomWeldingUnitPrice.year == year,
                )
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("删除基地 %s 年份 %s 的焊接工费单价: %s 条", location, year, count)
        return count

    def delete_unaudited_by_location_year(
        self, db: Session, location: str, year: int
    ) -> int:
        count = (
            db.query(BomWeldingUnitPrice)
            .filter(
                BomWeldingUnitPrice.location == location,
                BomWeldingUnitPrice.year == year,
                BomWeldingUnitPrice.audit_status != AUDIT_APPROVED,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(
            "删除未审核焊接工费单价: location=%s year=%s count=%s",
            location,
            year,
            count,
        )
        return count

    def approve_by_location_year(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        audited_by: str,
        audited_at: Any,
        audit_remark: Optional[str],
        updated_by: Optional[str] = None,
    ) -> int:
        values: Dict[Any, Any] = {
            BomWeldingUnitPrice.audit_status: AUDIT_APPROVED,
            BomWeldingUnitPrice.audited_by: audited_by,
            BomWeldingUnitPrice.audited_at: audited_at,
            BomWeldingUnitPrice.audit_remark: audit_remark,
        }
        if updated_by is not None:
            values[BomWeldingUnitPrice.updated_by] = updated_by
        count = (
            db.query(BomWeldingUnitPrice)
            .filter(
                BomWeldingUnitPrice.location == location,
                BomWeldingUnitPrice.year == year,
                BomWeldingUnitPrice.audit_status.in_([AUDIT_PENDING, AUDIT_REJECTED]),
            )
            .update(values, synchronize_session=False)
        )
        db.commit()
        return count

    def reverse_by_location_year(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        reverse_audited_by: str,
        reverse_audited_at: Any,
        reverse_audit_remark: str,
        updated_by: Optional[str] = None,
    ) -> int:
        values: Dict[Any, Any] = {
            BomWeldingUnitPrice.audit_status: AUDIT_PENDING,
            BomWeldingUnitPrice.reverse_audited_by: reverse_audited_by,
            BomWeldingUnitPrice.reverse_audited_at: reverse_audited_at,
            BomWeldingUnitPrice.reverse_audit_remark: reverse_audit_remark,
        }
        if updated_by is not None:
            values[BomWeldingUnitPrice.updated_by] = updated_by
        count = (
            db.query(BomWeldingUnitPrice)
            .filter(
                BomWeldingUnitPrice.location == location,
                BomWeldingUnitPrice.year == year,
                BomWeldingUnitPrice.audit_status == AUDIT_APPROVED,
            )
            .update(values, synchronize_session=False)
        )
        db.commit()
        return count
