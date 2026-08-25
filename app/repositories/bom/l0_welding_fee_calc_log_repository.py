"""BOM 焊接费计算批次日志 Repository。"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.models.bom import BomL0WeldingFeeCalcLog
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.bom_l0_welding_fee_dto import (
    BomL0WeldingFeeCalcLogCreate,
    BomL0WeldingFeeCalcLogPatch,
)

logger = logging.getLogger("repository.bom.l0_welding_fee_calc_log")

_STATUS_PROCESSING = "processing"

_PROCESSING_LOCK_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_bl0wf_calc_processing
ON bom_l0_welding_fee_calc_logs(year, location, vehicle_model, bom_version)
WHERE status = 'processing'
"""


class BomL0WeldingFeeCalcLogRepository:
    """计算批次日志数据访问。"""

    _lock_index_ensured = False

    def apply_processing_lock_index(self, conn: Connection) -> None:
        """在调用方连接上执行 DDL；不 commit（由 Service 提交）。"""
        conn.execute(text(_PROCESSING_LOCK_INDEX_SQL))

    def mark_processing_lock_index_ensured(self) -> None:
        BomL0WeldingFeeCalcLogRepository._lock_index_ensured = True

    def is_processing_lock_index_ensured(self) -> bool:
        return BomL0WeldingFeeCalcLogRepository._lock_index_ensured

    def get_by_id(self, db: Session, log_id: int) -> BomL0WeldingFeeCalcLog | None:
        return db.query(BomL0WeldingFeeCalcLog).filter(BomL0WeldingFeeCalcLog.id == log_id).first()

    def find_processing(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomL0WeldingFeeCalcLog | None:
        return (
            db.query(BomL0WeldingFeeCalcLog)
            .filter(
                BomL0WeldingFeeCalcLog.year == year,
                BomL0WeldingFeeCalcLog.location == location,
                BomL0WeldingFeeCalcLog.vehicle_model == vehicle_model,
                BomL0WeldingFeeCalcLog.bom_version == bom_version,
                BomL0WeldingFeeCalcLog.status == _STATUS_PROCESSING,
            )
            .order_by(BomL0WeldingFeeCalcLog.id.desc())
            .first()
        )

    def paginate(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomL0WeldingFeeCalcLog], int]:
        query = db.query(BomL0WeldingFeeCalcLog)
        if year is not None:
            query = query.filter(BomL0WeldingFeeCalcLog.year == year)
        if location:
            query = query.filter(BomL0WeldingFeeCalcLog.location == location)
        if vehicle_model:
            query = query.filter(BomL0WeldingFeeCalcLog.vehicle_model == vehicle_model)
        if bom_version:
            query = query.filter(BomL0WeldingFeeCalcLog.bom_version == bom_version)
        total = query.count()
        records = query.order_by(BomL0WeldingFeeCalcLog.id.desc()).offset(skip).limit(limit).all()
        return records, total

    def create(self, db: Session, data: BomL0WeldingFeeCalcLogCreate) -> BomL0WeldingFeeCalcLog:
        record = model_from_payload(BomL0WeldingFeeCalcLog, data)
        db.add(record)
        db.flush()
        return record

    def update(
        self, db: Session, log_id: int, data: BomL0WeldingFeeCalcLogPatch
    ) -> BomL0WeldingFeeCalcLog | None:
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
