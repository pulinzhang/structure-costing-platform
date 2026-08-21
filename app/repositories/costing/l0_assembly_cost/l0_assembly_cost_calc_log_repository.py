"""成品月核价 — 计算日志 Repository。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.costing.l0_assembly_cost_calc_log import L0AssemblyCostCalcLog


class L0AssemblyCostCalcLogRepository:
    def get_by_id(self, db: Session, log_id: int) -> L0AssemblyCostCalcLog | None:
        return (
            db.query(L0AssemblyCostCalcLog)
            .filter(L0AssemblyCostCalcLog.id == log_id)
            .first()
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
    ) -> L0AssemblyCostCalcLog | None:
        return (
            db.query(L0AssemblyCostCalcLog)
            .filter(
                L0AssemblyCostCalcLog.year == year,
                L0AssemblyCostCalcLog.month == month,
                L0AssemblyCostCalcLog.location == location,
                L0AssemblyCostCalcLog.vehicle_model == vehicle_model,
                L0AssemblyCostCalcLog.bom_version == bom_version,
                L0AssemblyCostCalcLog.status == "processing",
            )
            .order_by(L0AssemblyCostCalcLog.id.desc())
            .first()
        )

    def create(self, db: Session, row: L0AssemblyCostCalcLog) -> L0AssemblyCostCalcLog:
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
    ) -> tuple[list[L0AssemblyCostCalcLog], int]:
        q = db.query(L0AssemblyCostCalcLog)
        if year is not None:
            q = q.filter(L0AssemblyCostCalcLog.year == year)
        if month is not None:
            q = q.filter(L0AssemblyCostCalcLog.month == month)
        if location:
            q = q.filter(L0AssemblyCostCalcLog.location == location)
        if vehicle_model:
            q = q.filter(L0AssemblyCostCalcLog.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(L0AssemblyCostCalcLog.bom_version == bom_version)
        total = q.count()
        rows = (
            q.order_by(L0AssemblyCostCalcLog.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def delete(self, db: Session, log_id: int) -> bool:
        """删除计算日志（含 processing，作僵死锁兜底释放）。"""
        row = self.get_by_id(db, log_id)
        if row is None:
            return False
        db.delete(row)
        db.flush()
        return True

    def expire_stale_processing(
        self, db: Session, *, older_than: datetime, message: str
    ) -> int:
        rows = (
            db.query(L0AssemblyCostCalcLog)
            .filter(
                L0AssemblyCostCalcLog.status == "processing",
                L0AssemblyCostCalcLog.started_at.isnot(None),
                L0AssemblyCostCalcLog.started_at < older_than,
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
