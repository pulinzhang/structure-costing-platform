"""冲压零件价格核算计算批次日志 Repository。"""

import logging
from typing import Any, Optional, cast

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.costing import StampingPartCostCalcLog


logger = logging.getLogger("repository.stamping_part_cost_calc_log")

_STATUS_PROCESSING = "processing"

_PROCESSING_LOCK_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_spc_calc_processing
ON stamping_part_cost_calc_logs(year, month, location, stamping_supplier)
WHERE status = 'processing'
"""


class StampingPartCostCalcLogRepository:
    """计算批次日志数据访问。"""

    _lock_index_ensured = False

    def ensure_processing_lock_index(self, db: Session) -> None:
        if StampingPartCostCalcLogRepository._lock_index_ensured:
            return
        bind = cast(Engine, db.get_bind())
        with bind.connect() as conn:
            conn.execute(text(_PROCESSING_LOCK_INDEX_SQL))
            conn.commit()
        StampingPartCostCalcLogRepository._lock_index_ensured = True

    def get_by_id(
        self, db: Session, log_id: int
    ) -> Optional[StampingPartCostCalcLog]:
        return (
            db.query(StampingPartCostCalcLog)
            .filter(StampingPartCostCalcLog.id == log_id)
            .first()
        )

    def find_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str,
    ) -> Optional[StampingPartCostCalcLog]:
        return (
            db.query(StampingPartCostCalcLog)
            .filter(
                StampingPartCostCalcLog.year == year,
                StampingPartCostCalcLog.month == month,
                StampingPartCostCalcLog.location == location,
                StampingPartCostCalcLog.stamping_supplier == stamping_supplier,
                StampingPartCostCalcLog.status == _STATUS_PROCESSING,
            )
            .order_by(StampingPartCostCalcLog.id.desc())
            .first()
        )

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StampingPartCostCalcLog], int]:
        query = db.query(StampingPartCostCalcLog)
        if year is not None:
            query = query.filter(StampingPartCostCalcLog.year == year)
        if month is not None:
            query = query.filter(StampingPartCostCalcLog.month == month)
        if location:
            query = query.filter(StampingPartCostCalcLog.location == location)
        if stamping_supplier:
            query = query.filter(
                StampingPartCostCalcLog.stamping_supplier == stamping_supplier
            )
        total = query.count()
        records = (
            query.order_by(StampingPartCostCalcLog.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total

    def create(self, db: Session, data: dict[str, Any]) -> StampingPartCostCalcLog:
        record = StampingPartCostCalcLog(**data)
        db.add(record)
        db.flush()
        return record

    def update(
        self, db: Session, log_id: int, data: dict[str, Any]
    ) -> Optional[StampingPartCostCalcLog]:
        record = self.get_by_id(db, log_id)
        if record is None:
            return None
        for key, value in data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        db.flush()
        return record

    def delete(self, db: Session, log_id: int) -> bool:
        record = self.get_by_id(db, log_id)
        if record is None:
            return False
        db.delete(record)
        db.flush()
        return True
