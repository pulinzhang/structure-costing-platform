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

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_type: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SteelPrice], int]:
        query = db.query(SteelPrice)
        if year is not None:
            query = query.filter(SteelPrice.year == year)
        if month is not None:
            query = query.filter(SteelPrice.month == month)
        if steel_type:
            query = query.filter(SteelPrice.steel_type == steel_type)
        if grade:
            query = query.filter(SteelPrice.grade.contains(grade))
        if steel_mill:
            query = query.filter(SteelPrice.steel_mill == steel_mill)

        total = query.count()
        records = (
            query.order_by(
                SteelPrice.year.desc(),
                SteelPrice.month.desc(),
                SteelPrice.steel_type,
                SteelPrice.grade,
                SteelPrice.steel_mill,
                SteelPrice.thickness,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total

    def get_filter_options(self, db: Session) -> dict[str, list[Any]]:
        years = [
            row[0]
            for row in db.query(distinct(SteelPrice.year)).order_by(SteelPrice.year.desc()).all()
        ]
        months = [
            row[0]
            for row in db.query(distinct(SteelPrice.month)).order_by(SteelPrice.month).all()
        ]
        steel_types = [
            row[0]
            for row in db.query(distinct(SteelPrice.steel_type)).order_by(SteelPrice.steel_type).all()
        ]
        steel_mills = [
            row[0]
            for row in db.query(distinct(SteelPrice.steel_mill)).order_by(SteelPrice.steel_mill).all()
        ]
        return {
            "years": years,
            "months": months,
            "steel_types": steel_types,
            "steel_mills": steel_mills,
        }

    def create(self, db: Session, data: dict[str, Any]) -> SteelPrice:
        """插入新记录，失败时回滚后抛出 IntegrityError。"""
        record = SteelPrice(**data)
        db.add(record)
        db.flush()
        logger.info(
            "创建钢材价格: year=%s, month=%s, grade=%s, thickness=%s, id=%s",
            data.get("year"),
            data.get("month"),
            data.get("grade"),
            data.get("thickness"),
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
