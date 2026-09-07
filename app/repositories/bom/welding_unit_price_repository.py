"""
焊接工费单价 Repository
数据访问层，只负责与数据库交互
"""

import logging
from datetime import datetime
from typing import TypedDict

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Query, Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.bom import BomWeldingUnitPrice
from app.repositories.persist import apply_dto_fields, model_from_payload, query_update
from app.schemas.dto.bom_welding_unit_price_dto import (
    BomWeldingUnitPriceCreate,
    BomWeldingUnitPriceUpdate,
)

logger = logging.getLogger("repository.bom")


class AuditCountSummary(TypedDict):
    """列表筛选汇总：总条数 / 待审 / 已审。"""

    total_count: int
    pending_count: int
    approved_count: int


class WeldingUnitPriceListFilters(TypedDict):
    """焊接工费单价列表筛选体。"""

    locations: list[str]
    years: list[int]
    audit_status: str | None
    summary: AuditCountSummary


class BomWeldingUnitPriceRepository:
    """焊接工费单价数据访问"""

    def get_by_id(self, db: Session, id: int) -> BomWeldingUnitPrice | None:
        return db.query(BomWeldingUnitPrice).filter(BomWeldingUnitPrice.id == id).first()

    def get_by_location_year_item(
        self, db: Session, location: str, year: int, item_name: str
    ) -> BomWeldingUnitPrice | None:
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
    ) -> list[BomWeldingUnitPrice]:
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

    def list_by_year(self, db: Session, year: int) -> list[BomWeldingUnitPrice]:
        return (
            db.query(BomWeldingUnitPrice)
            .filter(BomWeldingUnitPrice.year == year)
            .order_by(BomWeldingUnitPrice.location, BomWeldingUnitPrice.item_name)
            .all()
        )

    def _build_list_query(
        self,
        db: Session,
        location: str | None = None,
        locations: list[str] | None = None,
        year: int | None = None,
        audit_status: str | None = None,
    ) -> Query[BomWeldingUnitPrice]:
        q = db.query(BomWeldingUnitPrice)
        if locations is not None:
            q = q.filter(BomWeldingUnitPrice.location.in_(locations))
        elif location is not None:
            q = q.filter(BomWeldingUnitPrice.location == location)
        if year is not None:
            q = q.filter(BomWeldingUnitPrice.year == year)
        if audit_status:
            q = q.filter(BomWeldingUnitPrice.audit_status == audit_status)
        return q

    def paginate(
        self,
        db: Session,
        location: str | None = None,
        locations: list[str] | None = None,
        year: int | None = None,
        audit_status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[BomWeldingUnitPrice], int]:
        q = self._build_list_query(
            db, location=location, locations=locations, year=year, audit_status=audit_status
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
        location: str | None = None,
        locations: list[str] | None = None,
        year: int | None = None,
        audit_status: str | None = None,
    ) -> AuditCountSummary:
        q = self._build_list_query(
            db, location=location, locations=locations, year=year, audit_status=audit_status
        )
        row = q.with_entities(
            func.count(BomWeldingUnitPrice.id).label("total_count"),
            func.sum(case((BomWeldingUnitPrice.audit_status == AUDIT_PENDING, 1), else_=0)).label(
                "pending_count"
            ),
            func.sum(case((BomWeldingUnitPrice.audit_status == AUDIT_APPROVED, 1), else_=0)).label(
                "approved_count"
            ),
        ).one()
        return {
            "total_count": int(row.total_count or 0),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
        }

    def list_for_export(
        self,
        db: Session,
        location: str | None = None,
        locations: list[str] | None = None,
        year: int | None = None,
        audit_status: str | None = None,
    ) -> list[BomWeldingUnitPrice]:
        q = self._build_list_query(
            db, location=location, locations=locations, year=year, audit_status=audit_status
        )
        return q.order_by(
            BomWeldingUnitPrice.location,
            BomWeldingUnitPrice.year,
            BomWeldingUnitPrice.item_name,
        ).all()

    def list_all(self, db: Session) -> list[BomWeldingUnitPrice]:
        return (
            db.query(BomWeldingUnitPrice)
            .order_by(
                BomWeldingUnitPrice.location,
                BomWeldingUnitPrice.year,
                BomWeldingUnitPrice.item_name,
            )
            .all()
        )

    def get_distinct_locations(self, db: Session) -> list[str]:
        results = (
            db.query(BomWeldingUnitPrice.location)
            .distinct()
            .order_by(BomWeldingUnitPrice.location)
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_years(self, db: Session) -> list[int]:
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
        statuses: list[str],
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
        self,
        db: Session,
        data: BomWeldingUnitPriceCreate,
        *,
        created_by: str,
        updated_by: str,
    ) -> BomWeldingUnitPrice:
        record = model_from_payload(BomWeldingUnitPrice, data)
        record.created_by = created_by
        record.updated_by = updated_by
        record.audit_status = AUDIT_PENDING
        db.add(record)
        db.flush()
        db.refresh(record)
        logger.info(
            "创建焊接工费单价: location=%s, year=%s, item=%s, id=%s",
            data.location,
            data.year,
            data.item_name,
            record.id,
        )
        return record

    def update(
        self,
        db: Session,
        id: int,
        update_data: BomWeldingUnitPriceUpdate,
        *,
        updated_by: str,
    ) -> BomWeldingUnitPrice | None:
        record = self.get_by_id(db, id)
        if not record:
            return None
        apply_dto_fields(record, update_data)
        record.updated_by = updated_by
        db.flush()
        db.refresh(record)
        logger.info("更新焊接工费单价: id=%s", id)
        return record

    def delete(self, db: Session, id: int) -> bool:
        record = self.get_by_id(db, id)
        if not record:
            return False
        db.delete(record)
        db.flush()
        logger.info("删除焊接工费单价: id=%s", id)
        return True

    def delete_unaudited_by_location_year(self, db: Session, location: str, year: int) -> int:
        count = (
            db.query(BomWeldingUnitPrice)
            .filter(
                BomWeldingUnitPrice.location == location,
                BomWeldingUnitPrice.year == year,
                BomWeldingUnitPrice.audit_status != AUDIT_APPROVED,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
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
            db.query(BomWeldingUnitPrice).filter(
                BomWeldingUnitPrice.location == location,
                BomWeldingUnitPrice.year == year,
                BomWeldingUnitPrice.audit_status == AUDIT_PENDING,
            ),
            values,
        )
        db.flush()
        return count

    def reverse_by_location_year(
        self,
        db: Session,
        *,
        location: str,
        year: int,
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
            db.query(BomWeldingUnitPrice).filter(
                BomWeldingUnitPrice.location == location,
                BomWeldingUnitPrice.year == year,
                BomWeldingUnitPrice.audit_status == AUDIT_APPROVED,
            ),
            values,
        )
        db.flush()
        return count
