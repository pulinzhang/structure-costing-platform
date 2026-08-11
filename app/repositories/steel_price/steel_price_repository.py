"""钢材价格 Repository，只负责数据库访问。"""

import logging
from typing import Any, Optional

from sqlalchemy import distinct
from sqlalchemy.orm import Session

from app.models.steel_price import SteelPrice


logger = logging.getLogger("repository.steel_price")


class SteelPriceRepository:
    """钢材价格数据访问。"""

    def get_by_id(self, db: Session, record_id: int) -> Optional[SteelPrice]:
        """根据 ID 查询单条记录。"""
        return db.query(SteelPrice).filter(SteelPrice.id == record_id).first()

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
        thickness,
        width,
    ) -> Optional[SteelPrice]:
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

        return (
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
            .all()
        )

    def get_filter_options(self, db: Session) -> dict[str, list[Any]]:
        years = [
            row[0]
            for row in db.query(distinct(SteelPrice.year)).order_by(SteelPrice.year.desc()).all()
        ]
        months = [
            row[0]
            for row in db.query(distinct(SteelPrice.month)).order_by(SteelPrice.month).all()
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
            for row in db.query(distinct(SteelPrice.steel_mill)).order_by(SteelPrice.steel_mill).all()
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

    def create(self, db: Session, data: dict[str, Any]) -> SteelPrice:
        """插入新记录。"""
        record = SteelPrice(**data)
        db.add(record)
        db.flush()
        logger.info(
            "创建钢材价格: year=%s month=%s location=%s grade=%s thickness=%s width=%s id=%s",
            data.get("year"),
            data.get("month"),
            data.get("location"),
            data.get("grade"),
            data.get("thickness"),
            data.get("width"),
            record.id,
        )
        return record

    def update(
        self,
        db: Session,
        record_id: int,
        update_data: dict[str, Any],
    ) -> Optional[SteelPrice]:
        """按主键更新记录，记录不存在时返回 None。"""
        record = self.get_by_id(db, record_id)
        if record is None:
            return None
        for column, value in update_data.items():
            if hasattr(record, column):
                setattr(record, column, value)
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
    ):
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
            .filter(SteelPrice.audit_status == "approved")
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
        ).filter(SteelPrice.audit_status != "approved")
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
        audited_at,
        audit_remark: str | None,
    ) -> int:
        """批量审核通过：pending/rejected → approved。返回更新条数。"""
        query = self._build_condition_query(
            db,
            year=year,
            month=month,
            location=location,
        ).filter(SteelPrice.audit_status.in_(["pending", "rejected"]))
        updated_count = query.update(
            {
                SteelPrice.audit_status: "approved",
                SteelPrice.audited_by: audited_by,
                SteelPrice.audited_at: audited_at,
                SteelPrice.audit_remark: audit_remark,
            },
            synchronize_session=False,
        )
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
        reverse_audited_at,
        reverse_audit_remark: str,
    ) -> int:
        """批量反审核：approved → pending。返回更新条数。"""
        query = self._build_condition_query(
            db,
            year=year,
            month=month,
            location=location,
        ).filter(SteelPrice.audit_status == "approved")
        updated_count = query.update(
            {
                SteelPrice.audit_status: "pending",
                SteelPrice.reverse_audited_by: reverse_audited_by,
                SteelPrice.reverse_audited_at: reverse_audited_at,
                SteelPrice.reverse_audit_remark: reverse_audit_remark,
            },
            synchronize_session=False,
        )
        db.flush()
        logger.info(
            "批量反审核: year=%s month=%s location=%s count=%s",
            year,
            month,
            location,
            updated_count,
        )
        return int(updated_count or 0)
