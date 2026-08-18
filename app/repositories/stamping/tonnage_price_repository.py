"""
冲次单价 Repository
数据访问层，只负责与数据库交互
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple, TypedDict

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Query, Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.stamping import StampingTonnagePrice
from app.repositories.persist import apply_dto_fields, model_from_payload, query_update
from app.schemas.dto.stamping_tonnage_price_dto import (
    StampingTonnagePriceCreate,
    StampingTonnagePriceUpdate,
)

logger = logging.getLogger("repository.stamping")


class AuditCountSummary(TypedDict):
    """列表筛选汇总：总条数 / 待审 / 已审。"""

    total_count: int
    pending_count: int
    approved_count: int


class TonnagePriceListFilters(TypedDict):
    """冲次单价列表筛选体。"""

    locations: list[str]
    years: list[int]
    tonnages: list[int]
    audit_status: str | None
    summary: AuditCountSummary


class StampingTonnagePriceRepository:
    """冲次单价数据访问"""

    def get_by_id(self, db: Session, id: int) -> Optional[StampingTonnagePrice]:
        """根据 ID 查询单条记录"""
        return db.query(StampingTonnagePrice).filter(StampingTonnagePrice.id == id).first()

    def get_by_location_year_tonnage(
        self, db: Session, location: str, year: int, tonnage: int
    ) -> Optional[StampingTonnagePrice]:
        """根据基地、年份和吨位查询记录"""
        return (
            db.query(StampingTonnagePrice)
            .filter(
                and_(
                    StampingTonnagePrice.location == location,
                    StampingTonnagePrice.year == year,
                    StampingTonnagePrice.tonnage == tonnage,
                )
            )
            .first()
        )

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> List[StampingTonnagePrice]:
        """查询指定基地+年份的所有记录"""
        return (
            db.query(StampingTonnagePrice)
            .filter(
                and_(
                    StampingTonnagePrice.location == location,
                    StampingTonnagePrice.year == year,
                )
            )
            .order_by(StampingTonnagePrice.tonnage)
            .all()
        )

    def list_by_year(self, db: Session, year: int) -> List[StampingTonnagePrice]:
        """查询指定年份的所有记录（跨基地）"""
        return (
            db.query(StampingTonnagePrice)
            .filter(StampingTonnagePrice.year == year)
            .order_by(StampingTonnagePrice.location, StampingTonnagePrice.tonnage)
            .all()
        )

    def _build_list_query(
        self,
        db: Session,
        location: Optional[str] = None,
        year: Optional[int] = None,
        audit_status: Optional[str] = None,
    ) -> Query[StampingTonnagePrice]:
        q = db.query(StampingTonnagePrice)
        if location is not None:
            q = q.filter(StampingTonnagePrice.location == location)
        if year is not None:
            q = q.filter(StampingTonnagePrice.year == year)
        if audit_status:
            q = q.filter(StampingTonnagePrice.audit_status == audit_status)
        return q

    def paginate(
        self,
        db: Session,
        location: Optional[str] = None,
        year: Optional[int] = None,
        audit_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[StampingTonnagePrice], int]:
        """分页查询"""
        q = self._build_list_query(
            db, location=location, year=year, audit_status=audit_status
        )
        total = q.count()
        records = (
            q.order_by(
                StampingTonnagePrice.location,
                StampingTonnagePrice.year,
                StampingTonnagePrice.tonnage,
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
    ) -> AuditCountSummary:
        """按筛选条件汇总条数 / 待审 / 已审。"""
        q = self._build_list_query(
            db, location=location, year=year, audit_status=audit_status
        )
        row = q.with_entities(
            func.count(StampingTonnagePrice.id).label("total_count"),
            func.sum(
                case((StampingTonnagePrice.audit_status == AUDIT_PENDING, 1), else_=0)
            ).label("pending_count"),
            func.sum(
                case((StampingTonnagePrice.audit_status == AUDIT_APPROVED, 1), else_=0)
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
    ) -> List[StampingTonnagePrice]:
        """按筛选条件导出全量记录（不分页）"""
        q = self._build_list_query(
            db, location=location, year=year, audit_status=audit_status
        )
        return (
            q.order_by(
                StampingTonnagePrice.location,
                StampingTonnagePrice.year,
                StampingTonnagePrice.tonnage,
            )
            .all()
        )

    def list_all(self, db: Session) -> List[StampingTonnagePrice]:
        """查询所有记录"""
        return (
            db.query(StampingTonnagePrice)
            .order_by(
                StampingTonnagePrice.location,
                StampingTonnagePrice.year,
                StampingTonnagePrice.tonnage,
            )
            .all()
        )

    def get_distinct_locations(self, db: Session) -> List[str]:
        """获取所有基地列表"""
        results = (
            db.query(StampingTonnagePrice.location)
            .distinct()
            .order_by(StampingTonnagePrice.location)
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_years(self, db: Session) -> List[int]:
        """获取所有年份列表"""
        results = (
            db.query(StampingTonnagePrice.year)
            .distinct()
            .order_by(StampingTonnagePrice.year.desc())
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_tonnages(self, db: Session) -> List[int]:
        """获取所有吨位列表"""
        results = (
            db.query(StampingTonnagePrice.tonnage)
            .distinct()
            .order_by(StampingTonnagePrice.tonnage)
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
            db.query(StampingTonnagePrice)
            .filter(
                StampingTonnagePrice.location == location,
                StampingTonnagePrice.year == year,
                StampingTonnagePrice.audit_status.in_(statuses),
            )
            .count()
        )

    def create(
        self,
        db: Session,
        data: StampingTonnagePriceCreate,
        *,
        created_by: str,
        updated_by: str,
        commit: bool = True,
    ) -> StampingTonnagePrice:
        """创建单条记录"""
        record = model_from_payload(StampingTonnagePrice, data)
        record.created_by = created_by
        record.updated_by = updated_by
        record.audit_status = AUDIT_PENDING
        db.add(record)
        if commit:
            db.commit()
        else:
            db.flush()
        db.refresh(record)
        logger.info(
            "创建冲次单价: location=%s, year=%s, tonnage=%s, id=%s",
            data.location,
            data.year,
            data.tonnage,
            record.id,
        )
        return record

    def bulk_create(
        self,
        db: Session,
        data_list: list[StampingTonnagePriceCreate],
        *,
        created_by: str,
        updated_by: str,
    ) -> list[StampingTonnagePrice]:
        """批量创建记录"""
        records: list[StampingTonnagePrice] = []
        for data in data_list:
            record = model_from_payload(StampingTonnagePrice, data)
            record.created_by = created_by
            record.updated_by = updated_by
            record.audit_status = AUDIT_PENDING
            records.append(record)
        db.add_all(records)
        db.commit()
        for record in records:
            db.refresh(record)
        logger.info("批量创建冲次单价: %s 条", len(records))
        return records

    def update(
        self,
        db: Session,
        id: int,
        update_data: StampingTonnagePriceUpdate,
        *,
        updated_by: str,
        commit: bool = True,
    ) -> Optional[StampingTonnagePrice]:
        """更新记录"""
        record = self.get_by_id(db, id)
        if not record:
            return None
        apply_dto_fields(record, update_data)
        record.updated_by = updated_by
        if commit:
            db.commit()
        else:
            db.flush()
        db.refresh(record)
        logger.info("更新冲次单价: id=%s", id)
        return record

    def delete(self, db: Session, id: int) -> bool:
        """删除记录"""
        record = self.get_by_id(db, id)
        if not record:
            return False
        db.delete(record)
        db.commit()
        logger.info("删除冲次单价: id=%s", id)
        return True

    def delete_unaudited_by_location_year(
        self, db: Session, location: str, year: int
    ) -> int:
        """仅删除未审核通过的记录（已通过跳过）"""
        count = (
            db.query(StampingTonnagePrice)
            .filter(
                StampingTonnagePrice.location == location,
                StampingTonnagePrice.year == year,
                StampingTonnagePrice.audit_status != AUDIT_APPROVED,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info(
            "删除未审核冲次单价: location=%s year=%s count=%s",
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
        audit_remark: Optional[str],
        updated_by: Optional[str] = None,
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
            db.query(StampingTonnagePrice).filter(
                StampingTonnagePrice.location == location,
                StampingTonnagePrice.year == year,
                StampingTonnagePrice.audit_status == AUDIT_PENDING,
            ),
            values,
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
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: Optional[str] = None,
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
            db.query(StampingTonnagePrice).filter(
                StampingTonnagePrice.location == location,
                StampingTonnagePrice.year == year,
                StampingTonnagePrice.audit_status == AUDIT_APPROVED,
            ),
            values,
        )
        db.commit()
        return count
