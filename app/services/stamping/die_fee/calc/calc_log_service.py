"""年度模具费计算日志与并发锁。"""

from __future__ import annotations

import contextlib
import logging
import uuid
from datetime import timedelta
from typing import cast

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.models.stamping.die_fee_calc_log import StampingDieFeeCalcLog
from app.repositories.stamping.die_fee_calc_log_repository import (
    StampingDieFeeCalcLogRepository,
)
from app.schemas.dto.stamping_die_fee_dto import (
    DieFeeCalcLogCreate,
    DieFeeCalcLogPatch,
    StampingDieFeeCalcDTO,
)
from app.schemas.vo.stamping_die_fee_vo import StampingDieFeeCalcLogVO
from app.services.stamping.die_fee.calc.constants import (
    DUPLICATE_SCOPE_CALC_MESSAGE,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STALE_PROCESSING_SECONDS,
)
from app.services.stamping.process_fee.calc.models import DuplicateScopeCalcError

logger = logging.getLogger("service.stamping.die_fee.calc.log")


class DieFeeCalcLogService:
    def __init__(
        self,
        calc_log_repo: StampingDieFeeCalcLogRepository | None = None,
    ) -> None:
        self.calc_log_repo = calc_log_repo or StampingDieFeeCalcLogRepository()

    def _ensure_processing_lock_index(self, db: Session) -> None:
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
        dto: StampingDieFeeCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> StampingDieFeeCalcLog:
        self._ensure_processing_lock_index(db)
        self.expire_stale_processing(
            db,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
        )
        existing = self.calc_log_repo.find_processing(
            db,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
        )
        if existing is not None:
            raise DuplicateScopeCalcError(DUPLICATE_SCOPE_CALC_MESSAGE)

        started_at = now()
        calc_batch_id = f"sdf-{uuid.uuid4().hex[:16]}"
        try:
            record = self.calc_log_repo.create(
                db,
                DieFeeCalcLogCreate(
                    calc_batch_id=calc_batch_id,
                    year=dto.year,
                    location=dto.location,
                    vehicle_model=dto.vehicle_model,
                    stamping_supplier=dto.stamping_supplier,
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
        with contextlib.suppress(Exception):
            db.rollback()
        self.calc_log_repo.update(
            db,
            log_id,
            DieFeeCalcLogPatch(
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
        vehicle_model: str,
    ) -> None:
        record = self.calc_log_repo.find_processing(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
        )
        if record is None or record.started_at is None:
            return
        if now() - record.started_at < timedelta(seconds=STALE_PROCESSING_SECONDS):
            return
        self.calc_log_repo.update(
            db,
            record.id,
            DieFeeCalcLogPatch(
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
        vehicle_model: str | None = None,
        stamping_supplier: str | None = None,
        version: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[StampingDieFeeCalcLogVO], int]:
        skip = (page - 1) * size
        rows, total = self.calc_log_repo.paginate(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            stamping_supplier=stamping_supplier,
            version=version,
            skip=skip,
            limit=size,
        )
        return [StampingDieFeeCalcLogVO.model_validate(r) for r in rows], total

    def get_calc_log(self, db: Session, log_id: int) -> StampingDieFeeCalcLogVO:
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            raise NotFoundException("计算日志不存在")
        return StampingDieFeeCalcLogVO.model_validate(record)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            raise NotFoundException("计算日志不存在")
        if record.status == STATUS_PROCESSING:
            raise BusinessException("计算进行中，禁止删除日志")
        deleted = self.calc_log_repo.delete(db, log_id)
        if not deleted:
            raise NotFoundException("计算日志不存在")
        db.commit()
