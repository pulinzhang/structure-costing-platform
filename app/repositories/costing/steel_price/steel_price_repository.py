"""钢材价格 Repository，只负责数据库访问。

查询见 queries.py，写入见 writes.py，形状见 types.py。
本文件是门面：独立查询/写入类，这里只委托。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.costing import SteelPrice
from app.repositories.costing.steel_price.queries import SteelPriceQueries
from app.repositories.costing.steel_price.types import (
    SteelPriceFilterOptionValues,
    SteelPriceFilterSummary,
)
from app.repositories.costing.steel_price.writes import SteelPriceWrites
from app.schemas.dto.steel_price_dto import SteelPricePatch, SteelPriceWrite

__all__ = [
    "SteelPriceRepository",
    "SteelPriceFilterOptionValues",
    "SteelPriceFilterSummary",
]


class SteelPriceRepository:
    """钢材价格数据访问。"""

    def __init__(self) -> None:
        self._queries = SteelPriceQueries()
        self._writes = SteelPriceWrites(self._queries)

    def get_by_id(self, db: Session, record_id: int) -> SteelPrice | None:
        return self._queries.get_by_id(db, record_id)

    def list_by_ids(self, db: Session, record_ids: list[int]) -> list[SteelPrice]:
        return self._queries.list_by_ids(db, record_ids)

    def list_distinct_years(self, db: Session) -> list[int]:
        return self._queries.list_distinct_years(db)

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
        return self._queries.get_by_business_key(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill,
            category_name=category_name,
            grade=grade,
            thickness=thickness,
            width=width,
        )

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
        steel_mill: str | None = None,
        audit_status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SteelPrice], int]:
        return self._queries.paginate(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
            skip=skip,
            limit=limit,
        )

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
        steel_mill: str | None = None,
        audit_status: str | None = None,
    ) -> SteelPriceFilterSummary:
        return self._queries.summarize_by_filters(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
        )

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
        steel_mill: str | None = None,
        audit_status: str | None = None,
    ) -> list[SteelPrice]:
        return self._queries.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            locations=locations,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
        )

    def get_filter_options(self, db: Session) -> SteelPriceFilterOptionValues:
        return self._queries.get_filter_options(db)

    def get_distinct_months_for_year(self, db: Session, year: int) -> list[int]:
        return self._queries.get_distinct_months_for_year(db, year)

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
        return self._queries.count_approved_by_conditions(
            db,
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
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
        return self._queries.count_by_conditions_and_statuses(
            db, year=year, month=month, location=location, statuses=statuses
        )

    def count_by_year_month_location(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
    ) -> int:
        return self._queries.count_by_year_month_location(
            db, year=year, month=month, location=location
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
        return self._queries.list_by_grade_thickness(
            db, year=year, month=month, location=location, grade=grade, thickness=thickness
        )

    def create(self, db: Session, data: SteelPriceWrite) -> SteelPrice:
        return self._writes.create(db, data)

    def update(
        self,
        db: Session,
        record_id: int,
        update_data: SteelPriceWrite | SteelPricePatch,
    ) -> SteelPrice | None:
        return self._writes.update(db, record_id, update_data)

    def delete(self, db: Session, record_id: int) -> bool:
        return self._writes.delete(db, record_id)

    def list_unaudited_ids(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
    ) -> list[int]:
        return self._writes.list_unaudited_ids(
            db,
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
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
        return self._writes.delete_unaudited_by_conditions(
            db,
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
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
        return self._writes.approve_by_period(
            db,
            year=year,
            month=month,
            location=location,
            audited_by=audited_by,
            audited_at=audited_at,
            audit_remark=audit_remark,
            updated_by=updated_by,
        )

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
        return self._writes.reverse_audit_by_period(
            db,
            year=year,
            month=month,
            location=location,
            reverse_audited_by=reverse_audited_by,
            reverse_audited_at=reverse_audited_at,
            reverse_audit_remark=reverse_audit_remark,
            updated_by=updated_by,
        )
