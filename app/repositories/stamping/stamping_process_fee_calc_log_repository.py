"""冲压加工费计算批次日志 Repository。"""

import logging

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.models.stamping import StampingProcessFeeCalcLog
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.stamping_process_fee_dto import (
    ProcessFeeCalcLogCreate,
    ProcessFeeCalcLogPatch,
)

logger = logging.getLogger("repository.stamping_process_fee_calc_log")

_STATUS_PROCESSING = "processing"

_PROCESSING_LOCK_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_spf_calc_processing
ON stamping_process_fee_calc_logs(year, location, stamping_supplier)
WHERE status = 'processing'
"""


class StampingProcessFeeCalcLogRepository:
    """计算批次日志数据访问。"""

    _lock_index_ensured = False

    def apply_processing_lock_index(self, conn: Connection) -> None:
        """在调用方连接上执行 DDL；不 commit（由 Service 提交）。"""
        conn.execute(text(_PROCESSING_LOCK_INDEX_SQL))

    def mark_processing_lock_index_ensured(self) -> None:
        StampingProcessFeeCalcLogRepository._lock_index_ensured = True

    def is_processing_lock_index_ensured(self) -> bool:
        return StampingProcessFeeCalcLogRepository._lock_index_ensured

    def get_by_id(self, db: Session, log_id: int) -> StampingProcessFeeCalcLog | None:
        return (
            db.query(StampingProcessFeeCalcLog)
            .filter(StampingProcessFeeCalcLog.id == log_id)
            .first()
        )

    def find_processing(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        stamping_supplier: str,
    ) -> StampingProcessFeeCalcLog | None:
        return (
            db.query(StampingProcessFeeCalcLog)
            .filter(
                StampingProcessFeeCalcLog.year == year,
                StampingProcessFeeCalcLog.location == location,
                StampingProcessFeeCalcLog.stamping_supplier == stamping_supplier,
                StampingProcessFeeCalcLog.status == _STATUS_PROCESSING,
            )
            .order_by(StampingProcessFeeCalcLog.id.desc())
            .first()
        )

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StampingProcessFeeCalcLog], int]:
        query = db.query(StampingProcessFeeCalcLog)
        if year is not None:
            query = query.filter(StampingProcessFeeCalcLog.year == year)
        if location:
            query = query.filter(StampingProcessFeeCalcLog.location == location)
        if stamping_supplier:
            query = query.filter(StampingProcessFeeCalcLog.stamping_supplier == stamping_supplier)
        total = query.count()
        records = (
            query.order_by(StampingProcessFeeCalcLog.id.desc()).offset(skip).limit(limit).all()
        )
        return records, total

    def create(self, db: Session, data: ProcessFeeCalcLogCreate) -> StampingProcessFeeCalcLog:
        record = model_from_payload(StampingProcessFeeCalcLog, data)
        db.add(record)
        db.flush()
        return record

    def update(
        self, db: Session, log_id: int, data: ProcessFeeCalcLogPatch
    ) -> StampingProcessFeeCalcLog | None:
        record = self.get_by_id(db, log_id)
        if record is None:
            return None
        apply_payload_fields(record, data)
        db.flush()
        return record

    def delete(self, db: Session, log_id: int) -> bool:
        record = self.get_by_id(db, log_id)
        if record is None:
            return False
        db.delete(record)
        db.flush()
        return True
