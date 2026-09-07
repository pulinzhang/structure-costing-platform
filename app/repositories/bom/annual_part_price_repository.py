"""
BOM 年度零件价 Repository
数据访问层：只负责查询构建与会话写入（flush），禁止 commit/rollback。
事务边界由 Service / Import Service 管理。
"""

import logging
from datetime import datetime
from typing import TypedDict

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Query, Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.bom import BomAnnualPartPrice
from app.repositories.persist import apply_dto_fields, model_from_payload, query_update
from app.schemas.dto.bom_annual_part_price_dto import (
    BomAnnualPartPriceCreate,
    BomAnnualPartPriceUpdate,
)

logger = logging.getLogger("repository.bom")


class AuditCountSummary(TypedDict):
    """列表筛选汇总：总条数 / 待审 / 已审。"""

    total_count: int
    pending_count: int
    approved_count: int


class AnnualPartPriceListFilters(TypedDict):
    """年度零件价列表筛选体。"""

    locations: list[str]
    years: list[int]
    audit_status: str | None
    summary: AuditCountSummary


class BomAnnualPartPriceRepository:
    """年度零件价数据访问"""

    def get_by_id(self, db: Session, id: int) -> BomAnnualPartPrice | None:
        return db.query(BomAnnualPartPrice).filter(BomAnnualPartPrice.id == id).first()

    def get_by_location_year_part_number(
        self, db: Session, location: str, year: int, part_number: str
    ) -> BomAnnualPartPrice | None:
        return (
            db.query(BomAnnualPartPrice)
            .filter(
                and_(
                    BomAnnualPartPrice.location == location,
                    BomAnnualPartPrice.year == year,
                    BomAnnualPartPrice.part_number == part_number,
                )
            )
            .first()
        )

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> list[BomAnnualPartPrice]:
        return (
            db.query(BomAnnualPartPrice)
            .filter(
                and_(
                    BomAnnualPartPrice.location == location,
                    BomAnnualPartPrice.year == year,
                )
            )
            .order_by(BomAnnualPartPrice.part_number)
            .all()
        )

    def count_with_unit_price(self, db: Session, *, location: str, year: int) -> int:
        return (
            db.query(BomAnnualPartPrice)
            .filter(
                BomAnnualPartPrice.location == location,
                BomAnnualPartPrice.year == year,
                BomAnnualPartPrice.unit_price.isnot(None),
            )
            .count()
        )

    def list_with_unit_price(
        self, db: Session, *, location: str, year: int
    ) -> list[BomAnnualPartPrice]:
        return (
            db.query(BomAnnualPartPrice)
            .filter(
                BomAnnualPartPrice.location == location,
                BomAnnualPartPrice.year == year,
                BomAnnualPartPrice.unit_price.isnot(None),
            )
            .order_by(BomAnnualPartPrice.part_number)
            .all()
        )

    def list_by_year(self, db: Session, year: int) -> list[BomAnnualPartPrice]:
        return (
            db.query(BomAnnualPartPrice)
            .filter(BomAnnualPartPrice.year == year)
            .order_by(
                BomAnnualPartPrice.location,
                BomAnnualPartPrice.part_number,
            )
            .all()
        )

    def _build_list_query(
        self,
        db: Session,
        location: str | None = None,
        locations: list[str] | None = None,
        year: int | None = None,
        audit_status: str | None = None,
        keyword: str | None = None,
    ) -> Query[BomAnnualPartPrice]:
        q = db.query(BomAnnualPartPrice)
        if locations is not None:
            q = q.filter(BomAnnualPartPrice.location.in_(locations))
        elif location is not None:
            q = q.filter(BomAnnualPartPrice.location == location)
        if year is not None:
            q = q.filter(BomAnnualPartPrice.year == year)
        if audit_status:
            q = q.filter(BomAnnualPartPrice.audit_status == audit_status)
        if keyword:
            pattern = f"%{keyword}%"
            q = q.filter(
                or_(
                    BomAnnualPartPrice.part_number.like(pattern),
                    BomAnnualPartPrice.part_name.like(pattern),
                )
            )
        return q

    def paginate(
        self,
        db: Session,
        location: str | None = None,
        locations: list[str] | None = None,
        year: int | None = None,
        audit_status: str | None = None,
        keyword: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[BomAnnualPartPrice], int]:
        q = self._build_list_query(
            db,
            location=location,
            locations=locations,
            year=year,
            audit_status=audit_status,
            keyword=keyword,
        )
        total = q.count()
        records = (
            q.order_by(
                BomAnnualPartPrice.location,
                BomAnnualPartPrice.year,
                BomAnnualPartPrice.part_number,
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
        keyword: str | None = None,
    ) -> AuditCountSummary:
        q = self._build_list_query(
            db,
            location=location,
            locations=locations,
            year=year,
            audit_status=audit_status,
            keyword=keyword,
        )
        row = q.with_entities(
            func.count(BomAnnualPartPrice.id).label("total_count"),
            func.sum(case((BomAnnualPartPrice.audit_status == AUDIT_PENDING, 1), else_=0)).label(
                "pending_count"
            ),
            func.sum(case((BomAnnualPartPrice.audit_status == AUDIT_APPROVED, 1), else_=0)).label(
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
        keyword: str | None = None,
    ) -> list[BomAnnualPartPrice]:
        q = self._build_list_query(
            db,
            location=location,
            locations=locations,
            year=year,
            audit_status=audit_status,
            keyword=keyword,
        )
        return q.order_by(
            BomAnnualPartPrice.location,
            BomAnnualPartPrice.year,
            BomAnnualPartPrice.part_number,
        ).all()

    def list_all(self, db: Session) -> list[BomAnnualPartPrice]:
        return (
            db.query(BomAnnualPartPrice)
            .order_by(
                BomAnnualPartPrice.location,
                BomAnnualPartPrice.year,
                BomAnnualPartPrice.part_number,
            )
            .all()
        )

    def get_distinct_locations(self, db: Session) -> list[str]:
        results = (
            db.query(BomAnnualPartPrice.location)
            .distinct()
            .order_by(BomAnnualPartPrice.location)
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_years(self, db: Session) -> list[int]:
        results = (
            db.query(BomAnnualPartPrice.year)
            .distinct()
            .order_by(BomAnnualPartPrice.year.desc())
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
            db.query(BomAnnualPartPrice)
            .filter(
                BomAnnualPartPrice.location == location,
                BomAnnualPartPrice.year == year,
                BomAnnualPartPrice.audit_status.in_(statuses),
            )
            .count()
        )

    def create(
        self,
        db: Session,
        data: BomAnnualPartPriceCreate,
        *,
        created_by: str,
        updated_by: str,
    ) -> BomAnnualPartPrice:
        """写入会话；由 Service 提交事务。"""
        record = model_from_payload(BomAnnualPartPrice, data)
        record.created_by = created_by
        record.updated_by = updated_by
        record.audit_status = AUDIT_PENDING
        db.add(record)
        db.flush()
        db.refresh(record)
        logger.info(
            "创建年度零件价: location=%s, year=%s, part=%s, id=%s",
            data.location,
            data.year,
            data.part_number,
            record.id,
        )
        return record

    def update(
        self,
        db: Session,
        id: int,
        update_data: BomAnnualPartPriceUpdate,
        *,
        updated_by: str,
    ) -> BomAnnualPartPrice | None:
        """写入会话；由 Service 提交事务。"""
        record = self.get_by_id(db, id)
        if not record:
            return None
        apply_dto_fields(record, update_data)
        record.updated_by = updated_by
        db.flush()
        db.refresh(record)
        logger.info("更新年度零件价: id=%s", id)
        return record

    def delete(self, db: Session, id: int) -> bool:
        """写入会话；由 Service 提交事务。"""
        record = self.get_by_id(db, id)
        if not record:
            return False
        db.delete(record)
        db.flush()
        logger.info("删除年度零件价: id=%s", id)
        return True

    def delete_unaudited_by_location_year(self, db: Session, location: str, year: int) -> int:
        """写入会话；由 Service 提交事务。"""
        count = (
            db.query(BomAnnualPartPrice)
            .filter(
                BomAnnualPartPrice.location == location,
                BomAnnualPartPrice.year == year,
                BomAnnualPartPrice.audit_status != AUDIT_APPROVED,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        logger.info(
            "删除未审核年度零件价: location=%s year=%s count=%s",
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
        """写入会话；由 Service 提交事务。"""
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_APPROVED,
            "audited_by": audited_by,
            "audited_at": audited_at,
            "audit_remark": audit_remark,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by
        count = query_update(
            db.query(BomAnnualPartPrice).filter(
                BomAnnualPartPrice.location == location,
                BomAnnualPartPrice.year == year,
                BomAnnualPartPrice.audit_status == AUDIT_PENDING,
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
        """写入会话；由 Service 提交事务。"""
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_PENDING,
            "reverse_audited_by": reverse_audited_by,
            "reverse_audited_at": reverse_audited_at,
            "reverse_audit_remark": reverse_audit_remark,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by
        count = query_update(
            db.query(BomAnnualPartPrice).filter(
                BomAnnualPartPrice.location == location,
                BomAnnualPartPrice.year == year,
                BomAnnualPartPrice.audit_status == AUDIT_APPROVED,
            ),
            values,
        )
        db.flush()
        return count
