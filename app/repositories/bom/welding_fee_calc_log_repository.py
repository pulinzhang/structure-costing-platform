"""BOM 焊接费计算批次日志 Repository。"""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session

from app.models.bom import BomWeldingFeeCalcLog
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.bom_welding_fee_dto import (
    BomWeldingFeeCalcLogCreate,
    BomWeldingFeeCalcLogPatch,
)

logger = logging.getLogger("repository.bom.welding_fee_calc_log")

_STATUS_PROCESSING = "processing"

_PROCESSING_LOCK_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_bwf_calc_processing
ON bom_welding_fee_calc_logs(year, location, vehicle_model, bom_version)
WHERE status = 'processing'
"""


class BomWeldingFeeCalcLogRepository:
    """计算批次日志数据访问。"""

    _lock_index_ensured = False

    def apply_processing_lock_index(self, conn: Connection) -> None:
        """在调用方连接上执行 DDL；不 commit（由 Service 提交）。"""
        conn.execute(text(_PROCESSING_LOCK_INDEX_SQL))

    def mark_processing_lock_index_ensured(self) -> None:
        BomWeldingFeeCalcLogRepository._lock_index_ensured = True

    def is_processing_lock_index_ensured(self) -> bool:
        return BomWeldingFeeCalcLogRepository._lock_index_ensured

    def get_by_id(self, db: Session, log_id: int) -> BomWeldingFeeCalcLog | None:
        return db.query(BomWeldingFeeCalcLog).filter(BomWeldingFeeCalcLog.id == log_id).first()

    def find_processing(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> BomWeldingFeeCalcLog | None:
        return (
            db.query(BomWeldingFeeCalcLog)
            .filter(
                BomWeldingFeeCalcLog.year == year,
                BomWeldingFeeCalcLog.location == location,
                BomWeldingFeeCalcLog.vehicle_model == vehicle_model,
                BomWeldingFeeCalcLog.bom_version == bom_version,
                BomWeldingFeeCalcLog.status == _STATUS_PROCESSING,
            )
            .order_by(BomWeldingFeeCalcLog.id.desc())
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
    ) -> tuple[list[BomWeldingFeeCalcLog], int]:
        query = db.query(BomWeldingFeeCalcLog)
        if year is not None:
            query = query.filter(BomWeldingFeeCalcLog.year == year)
        if location:
            query = query.filter(BomWeldingFeeCalcLog.location == location)
        if vehicle_model:
            query = query.filter(BomWeldingFeeCalcLog.vehicle_model == vehicle_model)
        if bom_version:
            query = query.filter(BomWeldingFeeCalcLog.bom_version == bom_version)
        total = query.count()
        records = query.order_by(BomWeldingFeeCalcLog.id.desc()).offset(skip).limit(limit).all()
        return records, total

    def create(self, db: Session, data: BomWeldingFeeCalcLogCreate) -> BomWeldingFeeCalcLog:
        record = model_from_payload(BomWeldingFeeCalcLog, data)
        db.add(record)
        db.flush()
        return record

    def update(
        self, db: Session, log_id: int, data: BomWeldingFeeCalcLogPatch
    ) -> BomWeldingFeeCalcLog | None:
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
