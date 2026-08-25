"""钢价计算批次日志 Repository。"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.models.costing import SteelPriceCalcLog
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.steel_price_dto import SteelPriceCalcLogCreate, SteelPriceCalcLogPatch


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

    def apply_processing_lock_index(self, conn: Connection) -> None:
        """在调用方连接上执行 DDL；不 commit（由 Service 提交）。"""
        conn.execute(text(_PROCESSING_LOCK_INDEX_SQL))

    def mark_processing_lock_index_ensured(self) -> None:
        SteelPriceCalcLogRepository._lock_index_ensured = True

    def is_processing_lock_index_ensured(self) -> bool:
        return SteelPriceCalcLogRepository._lock_index_ensured

    def get_by_id(self, db: Session, log_id: int) -> SteelPriceCalcLog | None:
        return db.query(SteelPriceCalcLog).filter(SteelPriceCalcLog.id == log_id).first()

    def get_by_batch_id(self, db: Session, calc_batch_id: str) -> SteelPriceCalcLog | None:
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
    ) -> SteelPriceCalcLog | None:
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
        records = query.order_by(SteelPriceCalcLog.id.desc()).offset(skip).limit(limit).all()
        return records, total

    def create(self, db: Session, data: SteelPriceCalcLogCreate) -> SteelPriceCalcLog:
        record = model_from_payload(SteelPriceCalcLog, data)
        db.add(record)
        db.flush()
        logger.info(
            "创建计算日志: batch=%s status=%s id=%s",
            data.calc_batch_id,
            data.status,
            record.id,
        )
        return record

    def update(
        self, db: Session, log_id: int, data: SteelPriceCalcLogPatch
    ) -> SteelPriceCalcLog | None:
        record = self.get_by_id(db, log_id)
        if record is None:
            return None
        apply_payload_fields(record, data)
        db.flush()
        logger.info(
            "更新计算日志: id=%s batch=%s status=%s",
            log_id,
            record.calc_batch_id,
            record.status,
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
