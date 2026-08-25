"""钢材价格 Repository，只负责数据库访问。"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import case, distinct, func
from sqlalchemy.orm import Query, Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.costing import SteelPrice
from app.repositories.persist import apply_payload_fields, model_from_payload, query_update
from app.schemas.dto.steel_price_dto import SteelPricePatch, SteelPriceWrite


class SteelPriceFilterSummary(TypedDict):
    """列表筛选汇总：均价 / 待审 / 已审。"""

    avg_final_price: Decimal | None
    pending_count: int
    approved_count: int


class SteelPriceFilterOptionValues(TypedDict):
    """筛选下拉选项（不含列表汇总，汇总由 Service 拼入）。"""

    years: list[int]
    months: list[int]
    locations: list[str]
    category_names: list[str]
    steel_mills: list[str]
    audit_statuses: list[str]


logger = logging.getLogger("repository.steel_price")

_UPDATE_SKIP = frozenset({"id", "created_by", "created_at"})


class SteelPriceRepository:
    """钢材价格数据访问。"""

    def get_by_id(self, db: Session, record_id: int) -> SteelPrice | None:
        """根据 ID 查询单条记录。"""
        return db.query(SteelPrice).filter(SteelPrice.id == record_id).first()

    def list_by_ids(self, db: Session, record_ids: list[int]) -> list[SteelPrice]:
        """按主键批量查询。"""
        if not record_ids:
            return []
        return db.query(SteelPrice).filter(SteelPrice.id.in_(record_ids)).all()

    def list_distinct_years(self, db: Session) -> list[int]:
        """去重年度，降序。"""
        return [
            row[0]
            for row in (db.query(distinct(SteelPrice.year)).order_by(SteelPrice.year.desc()).all())
            if row[0] is not None
        ]

    def get_by_business_key(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        steel_mill: str,
        category_name: str,
        grade: str,
        thickness: Decimal,
        width: Decimal,
    ) -> SteelPrice | None:
        """按业务唯一键查询。"""
        return (
            db.query(SteelPrice)
            .filter(
                SteelPrice.year == year,
                SteelPrice.month == month,
                SteelPrice.location == location,
                SteelPrice.steel_mill == steel_mill,
                SteelPrice.category_name == category_name,
                SteelPrice.grade == grade,
                SteelPrice.thickness == thickness,
                SteelPrice.width == width,
            )
            .first()
        )

    def _build_list_query(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
        audit_status: str | None = None,
    ) -> Query[SteelPrice]:
        query = db.query(SteelPrice)
        if year is not None:
            query = query.filter(SteelPrice.year == year)
        if month is not None:
            query = query.filter(SteelPrice.month == month)
        if location:
            query = query.filter(SteelPrice.location == location)
        if category_name:
            query = query.filter(SteelPrice.category_name == category_name)
        if grade:
            query = query.filter(SteelPrice.grade.contains(grade))
        if steel_mill:
            query = query.filter(SteelPrice.steel_mill == steel_mill)
        if audit_status:
            query = query.filter(SteelPrice.audit_status == audit_status)
        return query

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
        audit_status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SteelPrice], int]:
        query = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
        )
        total = query.count()
        records = (
            query.order_by(
                SteelPrice.year.desc(),
                SteelPrice.month.desc(),
                SteelPrice.location,
                SteelPrice.category_name,
                SteelPrice.grade,
                SteelPrice.steel_mill,
                SteelPrice.thickness,
                SteelPrice.width,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total

    def summarize_by_filters(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
        audit_status: str | None = None,
    ) -> SteelPriceFilterSummary:
        """按与列表相同的筛选条件汇总：均价 / 待审 / 已审。"""
        query = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
        )
        row = query.with_entities(
            func.avg(SteelPrice.final_price_per_ton).label("avg_final_price"),
            func.sum(case((SteelPrice.audit_status == AUDIT_PENDING, 1), else_=0)).label(
                "pending_count"
            ),
            func.sum(case((SteelPrice.audit_status == AUDIT_APPROVED, 1), else_=0)).label(
                "approved_count"
            ),
        ).one()
        avg_value = row.avg_final_price
        return {
            "avg_final_price": (Decimal(str(avg_value)) if avg_value is not None else None),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
        }

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
        audit_status: str | None = None,
    ) -> list[SteelPrice]:
        """导出用：按筛选条件取全量记录（含溯源字段）。"""
        query = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
        )
        return query.order_by(
            SteelPrice.year.desc(),
            SteelPrice.month.desc(),
            SteelPrice.location,
            SteelPrice.category_name,
            SteelPrice.grade,
            SteelPrice.steel_mill,
            SteelPrice.thickness,
            SteelPrice.width,
        ).all()

    def get_filter_options(self, db: Session) -> SteelPriceFilterOptionValues:
        years = [
            row[0]
            for row in db.query(distinct(SteelPrice.year)).order_by(SteelPrice.year.desc()).all()
        ]
        months = [
            row[0] for row in db.query(distinct(SteelPrice.month)).order_by(SteelPrice.month).all()
        ]
        locations = [
            row[0]
            for row in db.query(distinct(SteelPrice.location)).order_by(SteelPrice.location).all()
            if row[0]
        ]
        category_names = [
            row[0]
            for row in db.query(distinct(SteelPrice.category_name))
            .order_by(SteelPrice.category_name)
            .all()
            if row[0]
        ]
        steel_mills = [
            row[0]
            for row in db.query(distinct(SteelPrice.steel_mill))
            .order_by(SteelPrice.steel_mill)
            .all()
            if row[0]
        ]
        audit_statuses = [
            row[0]
            for row in db.query(distinct(SteelPrice.audit_status))
            .order_by(SteelPrice.audit_status)
            .all()
            if row[0]
        ]
        return {
            "years": years,
            "months": months,
            "locations": locations,
            "category_names": category_names,
            "steel_mills": steel_mills,
            "audit_statuses": audit_statuses,
        }

    def get_distinct_months_for_year(self, db: Session, year: int) -> list[int]:
        results = (
            db.query(distinct(SteelPrice.month))
            .filter(SteelPrice.year == year)
            .order_by(SteelPrice.month)
            .all()
        )
        return [int(row[0]) for row in results if row[0] is not None]

    def create(self, db: Session, data: SteelPriceWrite) -> SteelPrice:
        """插入新记录。"""
        record = model_from_payload(SteelPrice, data)
        db.add(record)
        db.flush()
        logger.info(
            "创建钢材价格: year=%s month=%s location=%s grade=%s thickness=%s width=%s id=%s",
            data.year,
            data.month,
            data.location,
            data.grade,
            data.thickness,
            data.width,
            record.id,
        )
        return record

    def update(
        self,
        db: Session,
        record_id: int,
        update_data: SteelPriceWrite | SteelPricePatch,
    ) -> SteelPrice | None:
        """按主键更新记录，记录不存在时返回 None。"""
        record = self.get_by_id(db, record_id)
        if record is None:
            return None
        apply_payload_fields(record, update_data, skip=_UPDATE_SKIP)
        db.flush()
        logger.info("更新钢材价格: id=%s", record_id)
        return record

    def delete(self, db: Session, record_id: int) -> bool:
        """按主键删除记录。"""
        record = self.get_by_id(db, record_id)
        if record is None:
            return False
        db.delete(record)
        db.flush()
        logger.info("删除钢材价格: id=%s", record_id)
        return True

    def _build_condition_query(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
    ) -> Query[SteelPrice]:
        query = db.query(SteelPrice).filter(
            SteelPrice.year == year,
            SteelPrice.month == month,
            SteelPrice.location == location,
        )
        if category_name:
            query = query.filter(SteelPrice.category_name == category_name)
        if grade:
            query = query.filter(SteelPrice.grade.contains(grade))
        if steel_mill:
            query = query.filter(SteelPrice.steel_mill == steel_mill)
        return query

    def count_approved_by_conditions(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
    ) -> int:
        """统计符合条件且已审核通过的条数。"""
        return (
            self._build_condition_query(
                db,
                year=year,
                month=month,
                location=location,
                category_name=category_name,
                grade=grade,
                steel_mill=steel_mill,
            )
            .filter(SteelPrice.audit_status == AUDIT_APPROVED)
            .count()
        )

    def delete_unaudited_by_conditions(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
    ) -> int:
        """按条件批量删除未审核记录（pending / rejected），返回删除条数。"""
        query = self._build_condition_query(
            db,
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
        ).filter(SteelPrice.audit_status != AUDIT_APPROVED)
        deleted_count = query.delete(synchronize_session=False)
        db.flush()
        logger.info(
            "批量删除未审核钢材价格: year=%s month=%s location=%s count=%s",
            year,
            month,
            location,
            deleted_count,
        )
        return deleted_count

    def count_by_conditions_and_statuses(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        statuses: list[str],
    ) -> int:
        """统计指定条件下、指定审核状态的条数。"""
        return (
            self._build_condition_query(
                db,
                year=year,
                month=month,
                location=location,
            )
            .filter(SteelPrice.audit_status.in_(statuses))
            .count()
        )

    def approve_by_period(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
        updated_by: str | None = None,
    ) -> int:
        """批量审核通过：pending/rejected → approved。返回更新条数。"""
        query = self._build_condition_query(
            db,
            year=year,
            month=month,
            location=location,
        ).filter(SteelPrice.audit_status.in_([AUDIT_PENDING, AUDIT_REJECTED]))
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_APPROVED,
            "audited_by": audited_by,
            "audited_at": audited_at,
            "audit_remark": audit_remark,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by
        updated_count = query_update(query, values)
        db.flush()
        logger.info(
            "批量审核通过: year=%s month=%s location=%s count=%s",
            year,
            month,
            location,
            updated_count,
        )
        return int(updated_count or 0)

    def reverse_audit_by_period(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: str | None = None,
    ) -> int:
        """批量反审核：approved → pending。返回更新条数。"""
        query = self._build_condition_query(
            db,
            year=year,
            month=month,
            location=location,
        ).filter(SteelPrice.audit_status == AUDIT_APPROVED)
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_PENDING,
            "reverse_audited_by": reverse_audited_by,
            "reverse_audited_at": reverse_audited_at,
            "reverse_audit_remark": reverse_audit_remark,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by
        updated_count = query_update(query, values)
        db.flush()
        logger.info(
            "批量反审核: year=%s month=%s location=%s count=%s",
            year,
            month,
            location,
            updated_count,
        )
        return int(updated_count or 0)

    def count_by_year_month_location(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
    ) -> int:
        """统计某基地某月钢材联动价条数。"""
        return (
            db.query(SteelPrice)
            .filter(
                SteelPrice.year == year,
                SteelPrice.month == month,
                SteelPrice.location == location,
            )
            .count()
        )

    def list_by_grade_thickness(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        grade: str,
        thickness: Decimal,
    ) -> list[SteelPrice]:
        """按年月/基地/牌号/料厚精确匹配（中标唯一钢厂场景）。"""
        return (
            db.query(SteelPrice)
            .filter(
                SteelPrice.year == year,
                SteelPrice.month == month,
                SteelPrice.location == location,
                SteelPrice.grade == grade,
                SteelPrice.thickness == thickness,
            )
            .all()
        )
