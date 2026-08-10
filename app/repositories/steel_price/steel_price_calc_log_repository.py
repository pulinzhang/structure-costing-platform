"""钢价计算批次日志 Repository。"""

import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.steel_price_calc_log import SteelPriceCalcLog


logger = logging.getLogger("repository.steel_price_calc_log")


class SteelPriceCalcLogRepository:
    """计算批次日志数据访问。"""

    def get_by_id(self, db: Session, log_id: int) -> Optional[SteelPriceCalcLog]:
        return db.query(SteelPriceCalcLog).filter(SteelPriceCalcLog.id == log_id).first()

    def get_by_batch_id(
        self, db: Session, calc_batch_id: str
    ) -> Optional[SteelPriceCalcLog]:
        return (
            db.query(SteelPriceCalcLog)
            .filter(SteelPriceCalcLog.calc_batch_id == calc_batch_id)
            .first()
        )

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SteelPriceCalcLog], int]:
        query = db.query(SteelPriceCalcLog)
        if year is not None:
            query = query.filter(SteelPriceCalcLog.year == year)
        if month is not None:
            query = query.filter(SteelPriceCalcLog.month == month)
        if location:
            query = query.filter(SteelPriceCalcLog.location == location)

        total = query.count()
        records = (
            query.order_by(SteelPriceCalcLog.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total

    def create(self, db: Session, data: dict[str, Any]) -> SteelPriceCalcLog:
        record = SteelPriceCalcLog(**data)
        db.add(record)
        db.flush()
        logger.info(
            "创建计算日志: batch=%s status=%s id=%s",
            data.get("calc_batch_id"),
            data.get("status"),
            record.id,
        )
        return record
