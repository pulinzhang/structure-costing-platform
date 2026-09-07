"""冲压零件价格核算计算批次日志 Repository。"""

import logging

from sqlalchemy import or_, text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.models.costing import StampingPartCostCalcLog
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostCalcLogCreate,
    StampingPartCostCalcLogPatch,
)

logger = logging.getLogger("repository.stamping_part_cost_calc_log")

_STATUS_PROCESSING = "processing"

_DROP_PROCESSING_LOCK_INDEX_SQL = "DROP INDEX IF EXISTS uq_spc_calc_processing"
_PROCESSING_LOCK_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_spc_calc_processing
ON stamping_part_cost_calc_logs(year, month, location, vehicle_model)
WHERE status = 'processing'
"""


class StampingPartCostCalcLogRepository:
    """计算批次日志数据访问。"""

    _lock_index_ensured = False

    def apply_processing_lock_index(self, conn: Connection) -> None:
        """在调用方连接上执行 DDL；不 commit（由 Service 提交）。"""
        conn.execute(text(_DROP_PROCESSING_LOCK_INDEX_SQL))
        conn.execute(text(_PROCESSING_LOCK_INDEX_SQL))

    def mark_processing_lock_index_ensured(self) -> None:
        StampingPartCostCalcLogRepository._lock_index_ensured = True

    def is_processing_lock_index_ensured(self) -> bool:
        return StampingPartCostCalcLogRepository._lock_index_ensured

    def get_by_id(self, db: Session, log_id: int) -> StampingPartCostCalcLog | None:
        return (
            db.query(StampingPartCostCalcLog).filter(StampingPartCostCalcLog.id == log_id).first()
        )

    def find_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str,
    ) -> StampingPartCostCalcLog | None:
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

    def list_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
    ) -> list[StampingPartCostCalcLog]:
        return (
            db.query(StampingPartCostCalcLog)
            .filter(
                StampingPartCostCalcLog.year == year,
                StampingPartCostCalcLog.month == month,
                StampingPartCostCalcLog.location == location,
                StampingPartCostCalcLog.status == _STATUS_PROCESSING,
                or_(
                    StampingPartCostCalcLog.vehicle_model == vehicle_model,
                    StampingPartCostCalcLog.vehicle_model.is_(None),
                ),
            )
            .all()
        )

    def get_latest(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str,
        vehicle_model: str | None = None,
    ) -> StampingPartCostCalcLog | None:
        query = db.query(StampingPartCostCalcLog).filter(
            StampingPartCostCalcLog.year == year,
            StampingPartCostCalcLog.month == month,
            StampingPartCostCalcLog.location == location,
            StampingPartCostCalcLog.stamping_supplier == stamping_supplier,
        )
        if vehicle_model:
            query = query.filter(StampingPartCostCalcLog.vehicle_model == vehicle_model)
        return query.order_by(StampingPartCostCalcLog.id.desc()).first()

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
            query = query.filter(StampingPartCostCalcLog.stamping_supplier == stamping_supplier)
        total = query.count()
        records = query.order_by(StampingPartCostCalcLog.id.desc()).offset(skip).limit(limit).all()
        return records, total

    def create(self, db: Session, data: StampingPartCostCalcLogCreate) -> StampingPartCostCalcLog:
        record = model_from_payload(StampingPartCostCalcLog, data)
        db.add(record)
        db.flush()
        return record

    def update(
        self, db: Session, log_id: int, data: StampingPartCostCalcLogPatch
    ) -> StampingPartCostCalcLog | None:
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

    def delete_all(self, db: Session) -> int:
        deleted = db.query(StampingPartCostCalcLog).delete(synchronize_session=False)
        db.flush()
        return int(deleted)
