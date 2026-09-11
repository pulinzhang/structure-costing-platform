"""成品月核价 — 计算日志 Repository。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.models.costing.assembly_cost_calc_log import AssemblyCostCalcLog

_STATUS_PROCESSING = "processing"

_PROCESSING_LOCK_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_assembly_calc_processing
ON costing_assembly_cost_calc_logs(year, month, location, vehicle_model, bom_version)
WHERE status = 'processing'
"""


class AssemblyCostCalcLogRepository:
    _lock_index_ensured = False

    def apply_processing_lock_index(self, conn: Connection) -> None:
        """在调用方连接上执行 DDL；不 commit（由 Service 提交）。"""
        conn.execute(text(_PROCESSING_LOCK_INDEX_SQL))

    def mark_processing_lock_index_ensured(self) -> None:
        AssemblyCostCalcLogRepository._lock_index_ensured = True

    def is_processing_lock_index_ensured(self) -> bool:
        return AssemblyCostCalcLogRepository._lock_index_ensured

    def get_by_id(self, db: Session, log_id: int) -> AssemblyCostCalcLog | None:
        return db.query(AssemblyCostCalcLog).filter(AssemblyCostCalcLog.id == log_id).first()

    def list_processing(self, db: Session) -> list[AssemblyCostCalcLog]:
        return (
            db.query(AssemblyCostCalcLog)
            .filter(AssemblyCostCalcLog.status == _STATUS_PROCESSING)
            .order_by(AssemblyCostCalcLog.id.asc())
            .all()
        )

    def get_processing_by_scope(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> AssemblyCostCalcLog | None:
        return (
            db.query(AssemblyCostCalcLog)
            .filter(
                AssemblyCostCalcLog.year == year,
                AssemblyCostCalcLog.month == month,
                AssemblyCostCalcLog.location == location,
                AssemblyCostCalcLog.vehicle_model == vehicle_model,
                AssemblyCostCalcLog.bom_version == bom_version,
                AssemblyCostCalcLog.status == _STATUS_PROCESSING,
            )
            .order_by(AssemblyCostCalcLog.id.desc())
            .first()
        )

    def create(self, db: Session, row: AssemblyCostCalcLog) -> AssemblyCostCalcLog:
        db.add(row)
        db.flush()
        return row

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AssemblyCostCalcLog], int]:
        q = db.query(AssemblyCostCalcLog)
        if year is not None:
            q = q.filter(AssemblyCostCalcLog.year == year)
        if month is not None:
            q = q.filter(AssemblyCostCalcLog.month == month)
        if location:
            q = q.filter(AssemblyCostCalcLog.location == location)
        if vehicle_model:
            q = q.filter(AssemblyCostCalcLog.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(AssemblyCostCalcLog.bom_version == bom_version)
        total = q.count()
        rows = q.order_by(AssemblyCostCalcLog.id.desc()).offset(skip).limit(limit).all()
        return rows, total

    def delete(self, db: Session, log_id: int) -> bool:
        """删除计算日志（含 processing，作僵死锁兜底释放）。"""
        row = self.get_by_id(db, log_id)
        if row is None:
            return False
        db.delete(row)
        db.flush()
        return True

    def delete_all(self, db: Session) -> int:
        deleted = db.query(AssemblyCostCalcLog).delete(synchronize_session=False)
        db.flush()
        return int(deleted)

    def expire_stale_processing(self, db: Session, *, older_than: datetime, message: str) -> int:
        rows = (
            db.query(AssemblyCostCalcLog)
            .filter(
                AssemblyCostCalcLog.status == _STATUS_PROCESSING,
                AssemblyCostCalcLog.started_at.isnot(None),
                AssemblyCostCalcLog.started_at < older_than,
            )
            .all()
        )
        for row in rows:
            row.status = "failed"
            row.message = message
            row.finished_at = datetime.utcnow()
        if rows:
            db.flush()
        return len(rows)
