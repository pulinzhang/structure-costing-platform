"""BOM 焊接工艺拆解 — 生成批次日志 Repository。"""

from __future__ import annotations

import logging
from typing import Any, Optional, cast

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.bom_welding_process_breakdown_generate_log import (
    BomWeldingProcessBreakdownGenerateLog,
)

logger = logging.getLogger("repository.bom.welding_process_breakdown_generate_log")

_STATUS_PROCESSING = "processing"

_PROCESSING_LOCK_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS uq_wpb_gen_processing
ON bom_welding_process_breakdown_generate_logs(location, vehicle_model, bom_version)
WHERE status = 'processing'
"""


class BomWeldingProcessBreakdownGenerateLogRepository:
    """生成批次日志数据访问。"""

    _lock_index_ensured = False

    def ensure_processing_lock_index(self, db: Session) -> None:
        if BomWeldingProcessBreakdownGenerateLogRepository._lock_index_ensured:
            return
        bind = cast(Engine, db.get_bind())
        with bind.connect() as conn:
            conn.execute(text(_PROCESSING_LOCK_INDEX_SQL))
            conn.commit()
        BomWeldingProcessBreakdownGenerateLogRepository._lock_index_ensured = True

    def get_by_id(
        self, db: Session, log_id: int
    ) -> Optional[BomWeldingProcessBreakdownGenerateLog]:
        return (
            db.query(BomWeldingProcessBreakdownGenerateLog)
            .filter(BomWeldingProcessBreakdownGenerateLog.id == log_id)
            .first()
        )

    def find_processing(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> Optional[BomWeldingProcessBreakdownGenerateLog]:
        return (
            db.query(BomWeldingProcessBreakdownGenerateLog)
            .filter(
                BomWeldingProcessBreakdownGenerateLog.location == location,
                BomWeldingProcessBreakdownGenerateLog.vehicle_model == vehicle_model,
                BomWeldingProcessBreakdownGenerateLog.bom_version == bom_version,
                BomWeldingProcessBreakdownGenerateLog.status == _STATUS_PROCESSING,
            )
            .order_by(BomWeldingProcessBreakdownGenerateLog.id.desc())
            .first()
        )

    def paginate(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[BomWeldingProcessBreakdownGenerateLog], int]:
        query = db.query(BomWeldingProcessBreakdownGenerateLog)
        if location:
            query = query.filter(
                BomWeldingProcessBreakdownGenerateLog.location == location
            )
        if vehicle_model:
            query = query.filter(
                BomWeldingProcessBreakdownGenerateLog.vehicle_model == vehicle_model
            )
        if bom_version:
            query = query.filter(
                BomWeldingProcessBreakdownGenerateLog.bom_version == bom_version
            )
        total = query.count()
        records = (
            query.order_by(BomWeldingProcessBreakdownGenerateLog.id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total

    def create(
        self, db: Session, data: dict[str, Any]
    ) -> BomWeldingProcessBreakdownGenerateLog:
        record = BomWeldingProcessBreakdownGenerateLog(**data)
        db.add(record)
        db.flush()
        return record

    def update(
        self, db: Session, log_id: int, data: dict[str, Any]
    ) -> Optional[BomWeldingProcessBreakdownGenerateLog]:
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
