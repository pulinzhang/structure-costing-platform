"""钢材价格查询：列表、导出、汇总、下拉、牌号料厚匹配。"""

from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Query, Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.costing import SteelPrice
from app.repositories.costing.steel_price.types import (
    SteelPriceFilterOptionValues,
    SteelPriceFilterSummary,
)


class SteelPriceQueries:
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
            for row in db.query(SteelPrice.year).distinct().order_by(SteelPrice.year.desc()).all()
            if row[0] is not None
        ]

    def get_by_business_key(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        steel_mill_id: int,
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
                SteelPrice.steel_mill_id == steel_mill_id,
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
        locations: list[str] | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill_id: int | None = None,
        audit_status: str | None = None,
    ) -> Query[SteelPrice]:
        query = db.query(SteelPrice)
        if year is not None:
            query = query.filter(SteelPrice.year == year)
        if month is not None:
            query = query.filter(SteelPrice.month == month)
        if locations is not None:
            query = query.filter(SteelPrice.location.in_(locations))
        elif location:
            query = query.filter(SteelPrice.location == location)
        if category_name:
            query = query.filter(SteelPrice.category_name == category_name)
        if grade:
            query = query.filter(SteelPrice.grade.contains(grade))
        if steel_mill_id is not None:
            query = query.filter(SteelPrice.steel_mill_id == steel_mill_id)
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
        locations: list[str] | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill_id: int | None = None,
        audit_status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SteelPrice], int, SteelPriceFilterSummary]:
        query = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            category_name=category_name,
            grade=grade,
            steel_mill_id=steel_mill_id,
            audit_status=audit_status,
        )
        total, summary = self._count_and_summarize(query)
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
        return records, total, summary

    def _count_and_summarize(self, query: Query[SteelPrice]) -> tuple[int, SteelPriceFilterSummary]:
        """同一套筛选：总条数、均价、待审、已审，一次聚合。"""
        row = query.with_entities(
            func.count(SteelPrice.id).label("total"),
            func.avg(SteelPrice.final_price_per_ton).label("avg_final_price"),
            func.sum(case((SteelPrice.audit_status == AUDIT_PENDING, 1), else_=0)).label(
                "pending_count"
            ),
            func.sum(case((SteelPrice.audit_status == AUDIT_APPROVED, 1), else_=0)).label(
                "approved_count"
            ),
        ).one()
        avg_value = row.avg_final_price
        summary: SteelPriceFilterSummary = {
            "avg_final_price": Decimal(str(avg_value)) if avg_value is not None else None,
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
        }
        return int(row.total or 0), summary

    def summarize_by_filters(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill_id: int | None = None,
        audit_status: str | None = None,
    ) -> SteelPriceFilterSummary:
        """按与列表相同的筛选条件汇总：均价 / 待审 / 已审。"""
        query = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            category_name=category_name,
            grade=grade,
            steel_mill_id=steel_mill_id,
            audit_status=audit_status,
        )
        _total, summary = self._count_and_summarize(query)
        return summary

    def list_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        locations: list[str] | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill_id: int | None = None,
        audit_status: str | None = None,
    ) -> list[SteelPrice]:
        """导出用：按筛选条件取全量记录（含溯源字段）。"""
        query = self._build_list_query(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            category_name=category_name,
            grade=grade,
            steel_mill_id=steel_mill_id,
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
            for row in db.query(SteelPrice.year).distinct().order_by(SteelPrice.year.desc()).all()
        ]
        months = [
            row[0] for row in db.query(SteelPrice.month).distinct().order_by(SteelPrice.month).all()
        ]
        locations = [
            row[0]
            for row in db.query(SteelPrice.location).distinct().order_by(SteelPrice.location).all()
            if row[0]
        ]
        category_names = [
            row[0]
            for row in db.query(SteelPrice.category_name)
            .distinct()
            .order_by(SteelPrice.category_name)
            .all()
            if row[0]
        ]
        audit_statuses = [
            row[0]
            for row in db.query(SteelPrice.audit_status)
            .distinct()
            .order_by(SteelPrice.audit_status)
            .all()
            if row[0]
        ]
        return {
            "years": years,
            "months": months,
            "locations": locations,
            "category_names": category_names,
            "audit_statuses": audit_statuses,
        }

    def get_distinct_months_for_year(self, db: Session, year: int) -> list[int]:
        results = (
            db.query(SteelPrice.month)
            .distinct()
            .filter(SteelPrice.year == year)
            .order_by(SteelPrice.month)
            .all()
        )
        return [int(row[0]) for row in results if row[0] is not None]

    def _build_condition_query(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill_id: int | None = None,
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
        if steel_mill_id is not None:
            query = query.filter(SteelPrice.steel_mill_id == steel_mill_id)
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
        steel_mill_id: int | None = None,
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
                steel_mill_id=steel_mill_id,
            )
            .filter(SteelPrice.audit_status == AUDIT_APPROVED)
            .count()
        )

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
        """按年月/基地/牌号/料厚匹配（大类取价后可能多钢厂）。"""
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
