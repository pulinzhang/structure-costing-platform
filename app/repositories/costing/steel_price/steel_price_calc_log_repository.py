"""钢价计算批次日志 Repository。"""

import logging
from typing import Any, Optional, cast

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.steel_price_calc_log import SteelPriceCalcLog


logger = logging.getLogger("repository.steel_price_calc_log")

# 与 CalcLog status 约定一致；Repository 不依赖 Service 层常量，避免循环导入
_STATUS_PROCESSING = "processing"

_PROCESSING_LOCK_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_steel_price_calc_processing
ON steel_price_calc_logs(year, month, location)
WHERE status = 'processing'
"""


class SteelPriceCalcLogRepository:
    """计算批次日志数据访问。"""

    _lock_index_ensured = False

    def ensure_processing_lock_index(self, db: Session) -> None:
        """确保 SQLite 部分唯一索引存在（独立连接，幂等）。"""
        if SteelPriceCalcLogRepository._lock_index_ensured:
            return
        # DDL 用独立连接，避免与业务事务 rollback 互相干扰
        bind = cast(Engine, db.get_bind())
        with bind.connect() as conn:
            conn.execute(text(_PROCESSING_LOCK_INDEX_SQL))
            conn.commit()
        SteelPriceCalcLogRepository._lock_index_ensured = True

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

    def find_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
    ) -> Optional[SteelPriceCalcLog]:
        return (
            db.query(SteelPriceCalcLog)
            .filter(
                SteelPriceCalcLog.year == year,
                SteelPriceCalcLog.month == month,
                SteelPriceCalcLog.location == location,
                SteelPriceCalcLog.status == _STATUS_PROCESSING,
            )
            .order_by(SteelPriceCalcLog.id.desc())
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

    def update(
        self, db: Session, log_id: int, data: dict[str, Any]
    ) -> Optional[SteelPriceCalcLog]:
        record = self.get_by_id(db, log_id)
        if record is None:
            return None
        for key, value in data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        db.flush()
        logger.info(
            "更新计算日志: id=%s batch=%s status=%s",
            log_id,
            record.calc_batch_id,
            getattr(record, "status", None),
        )
        return record

    def delete(self, db: Session, log_id: int) -> bool:
        record = self.get_by_id(db, log_id)
        if record is None:
            return False
        db.delete(record)
        db.flush()
        logger.info("删除计算日志: id=%s batch=%s", log_id, record.calc_batch_id)
        return True

