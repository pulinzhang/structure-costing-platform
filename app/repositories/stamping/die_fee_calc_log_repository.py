"""冲压年度模具费计算日志 Repository。"""

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.models.stamping.die_fee_calc_log import StampingDieFeeCalcLog
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.stamping_die_fee_dto import DieFeeCalcLogCreate, DieFeeCalcLogPatch

_STATUS_PROCESSING = "processing"

_PROCESSING_LOCK_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_sdf_calc_processing
ON stamping_die_fee_calc_logs(year, location, vehicle_model)
WHERE status = 'processing'
"""


class StampingDieFeeCalcLogRepository:
    _lock_index_ensured = False

    def apply_processing_lock_index(self, conn: Connection) -> None:
        conn.execute(text(_PROCESSING_LOCK_INDEX_SQL))

    def mark_processing_lock_index_ensured(self) -> None:
        StampingDieFeeCalcLogRepository._lock_index_ensured = True

    def is_processing_lock_index_ensured(self) -> bool:
        return StampingDieFeeCalcLogRepository._lock_index_ensured

    def get_by_id(self, db: Session, log_id: int) -> StampingDieFeeCalcLog | None:
        return db.query(StampingDieFeeCalcLog).filter(StampingDieFeeCalcLog.id == log_id).first()

    def find_processing(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
    ) -> StampingDieFeeCalcLog | None:
        return (
            db.query(StampingDieFeeCalcLog)
            .filter(
                StampingDieFeeCalcLog.year == year,
                StampingDieFeeCalcLog.location == location,
                StampingDieFeeCalcLog.vehicle_model == vehicle_model,
                StampingDieFeeCalcLog.status == _STATUS_PROCESSING,
            )
            .order_by(StampingDieFeeCalcLog.id.desc())
            .first()
        )

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[StampingDieFeeCalcLog], int]:
        query = db.query(StampingDieFeeCalcLog)
        if year is not None:
            query = query.filter(StampingDieFeeCalcLog.year == year)
        if location:
            query = query.filter(StampingDieFeeCalcLog.location == location)
        if vehicle_model:
            query = query.filter(StampingDieFeeCalcLog.vehicle_model == vehicle_model)
        total = query.count()
        rows = query.order_by(StampingDieFeeCalcLog.id.desc()).offset(skip).limit(limit).all()
        return rows, total

    def create(self, db: Session, data: DieFeeCalcLogCreate) -> StampingDieFeeCalcLog:
        record = model_from_payload(StampingDieFeeCalcLog, data)
        db.add(record)
        db.flush()
        return record

    def update(
        self, db: Session, log_id: int, data: DieFeeCalcLogPatch
    ) -> StampingDieFeeCalcLog | None:
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
