"""加工费计算日志：锁、过期释放、CRUD。"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import cast

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.stamping import StampingProcessFeeCalcLog
from app.repositories.stamping.stamping_process_fee_calc_log_repository import (
    StampingProcessFeeCalcLogRepository,
)
from app.schemas.dto.stamping_process_fee_dto import (
    ProcessFeeCalcLogCreate,
    ProcessFeeCalcLogPatch,
    StampingProcessFeeCalcDTO,
)
from app.schemas.vo.stamping_process_fee_vo import StampingProcessFeeCalcLogVO
from app.services.stamping.process_fee.calc.constants import (
    DUPLICATE_SCOPE_CALC_MESSAGE,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STALE_PROCESSING_SECONDS,
)
from app.services.stamping.process_fee.calc.models import DuplicateScopeCalcError
from app.services.stamping.process_fee.scope import require_scope


class ProcessFeeCalcLogService:
    """计算日志与并发锁。"""

    def __init__(
        self,
        calc_log_repo: StampingProcessFeeCalcLogRepository | None = None,
    ) -> None:
        self.calc_log_repo = calc_log_repo or StampingProcessFeeCalcLogRepository()

    def _ensure_processing_lock_index(self, db: Session) -> None:
        """DDL 用独立连接；commit 在 Service（不进业务 Session）。"""
        if self.calc_log_repo.is_processing_lock_index_ensured():
            return
        bind = cast(Engine, db.get_bind())
        with bind.connect() as conn:
            self.calc_log_repo.apply_processing_lock_index(conn)
            conn.commit()
        self.calc_log_repo.mark_processing_lock_index_ensured()

    def begin_processing(
        self,
        db: Session,
        dto: StampingProcessFeeCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> StampingProcessFeeCalcLog:
        location, supplier = require_scope(dto)
        self._ensure_processing_lock_index(db)
        self.expire_stale_processing(
            db,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
        )
        existing = self.calc_log_repo.find_processing(
            db,
            year=dto.year,
            location=location,
            stamping_supplier=supplier,
        )
        if existing is not None:
            raise DuplicateScopeCalcError(DUPLICATE_SCOPE_CALC_MESSAGE)

        started_at = now()
        calc_batch_id = f"spf-{uuid.uuid4().hex[:16]}"
        try:
            record = self.calc_log_repo.create(
                db,
                ProcessFeeCalcLogCreate(
                    calc_batch_id=calc_batch_id,
                    year=dto.year,
                    location=location,
                    stamping_supplier=supplier,
                    vehicle_model=dto.vehicle_model,
                    version=dto.version,
                    status=STATUS_PROCESSING,
                    detail_text="计算进行中...",
                    started_at=started_at,
                    operator_id=operator_id,
                    operator_name=operator_name,
                    created_by=operator_name,
                    updated_by=operator_name,
                ),
            )
            db.commit()
            db.refresh(record)
            return record
        except IntegrityError as error:
            db.rollback()
            raise DuplicateScopeCalcError(DUPLICATE_SCOPE_CALC_MESSAGE) from error

    def mark_log_failed(
        self,
        db: Session,
        *,
        log_id: int,
        detail_text: str,
    ) -> None:
        self.calc_log_repo.update(
            db,
            log_id,
            ProcessFeeCalcLogPatch(
                status=STATUS_FAILED,
                detail_text=detail_text,
                finished_at=now(),
            ),
        )
        db.commit()

    def expire_stale_processing(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        stamping_supplier: str,
    ) -> None:
        record = self.calc_log_repo.find_processing(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
        )
        if record is None or record.started_at is None:
            return
        if now() - record.started_at < timedelta(seconds=STALE_PROCESSING_SECONDS):
            return
        self.calc_log_repo.update(
            db,
            record.id,
            ProcessFeeCalcLogPatch(
                status=STATUS_FAILED,
                detail_text=(record.detail_text or "") + "\n超时自动释放计算锁",
                finished_at=now(),
            ),
        )
        db.commit()

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[StampingProcessFeeCalcLogVO], int]:
        skip = (page - 1) * size
        rows, total = self.calc_log_repo.paginate(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            skip=skip,
            limit=size,
        )
        return [StampingProcessFeeCalcLogVO.model_validate(r) for r in rows], total

    def get_calc_log(
        self, db: Session, log_id: int
    ) -> StampingProcessFeeCalcLogVO | None:
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            return None
        return StampingProcessFeeCalcLogVO.model_validate(record)

    def delete_calc_log(self, db: Session, log_id: int) -> bool:
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            return False
        if record.status == STATUS_PROCESSING:
            raise BusinessException("计算进行中，无法删除该记录")
        deleted = self.calc_log_repo.delete(db, log_id)
        if deleted:
            db.commit()
        return deleted
