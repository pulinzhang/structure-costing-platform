"""冲压零件核价计算日志与范围锁。"""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.costing import StampingPartCostCalcLog
from app.repositories.costing.stamping_part_cost.stamping_part_cost_calc_log_repository import (
    StampingPartCostCalcLogRepository,
)
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.schemas.vo.stamping_part_cost_vo import StampingPartCostCalcLogVO
from app.services.costing.stamping_part_cost.calc.constants import (
    DUPLICATE_SCOPE_CALC_MESSAGE,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STALE_PROCESSING_SECONDS,
)
from app.services.costing.stamping_part_cost.calc.models import DuplicateScopeCalcError
from app.services.costing.stamping_part_cost.calc.scope import require_scope


class PartCostCalcLogService:
    """计算锁、超时释放与计算日志查询。"""

    def __init__(
        self,
        calc_log_repo: StampingPartCostCalcLogRepository | None = None,
    ) -> None:
        self.calc_log_repo = calc_log_repo or StampingPartCostCalcLogRepository()

    def begin_processing(
        self,
        db: Session,
        dto: StampingPartCostCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> StampingPartCostCalcLog:
        location, supplier = require_scope(dto)
        self.calc_log_repo.ensure_processing_lock_index(db)
        self.expire_stale_processing(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )
        existing = self.calc_log_repo.find_processing(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            stamping_supplier=supplier,
        )
        if existing is not None:
            raise DuplicateScopeCalcError(DUPLICATE_SCOPE_CALC_MESSAGE)

        started_at = now()
        calc_batch_id = f"spc-{uuid.uuid4().hex[:16]}"
        try:
            record = self.calc_log_repo.create(
                db,
                {
                    "calc_batch_id": calc_batch_id,
                    "year": dto.year,
                    "month": dto.month,
                    "location": location,
                    "stamping_supplier": supplier,
                    "vehicle_model": dto.vehicle_model,
                    "version": dto.version,
                    "status": STATUS_PROCESSING,
                    "detail_text": "计算进行中...",
                    "started_at": started_at,
                    "operator_id": operator_id,
                    "operator_name": operator_name,
                    "created_by": operator_name,
                    "updated_by": operator_name,
                },
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
            {
                "status": STATUS_FAILED,
                "detail_text": detail_text,
                "finished_at": now(),
            },
        )
        db.commit()

    def expire_stale_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str,
    ) -> None:
        record = self.calc_log_repo.find_processing(
            db,
            year=year,
            month=month,
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
            {
                "status": STATUS_FAILED,
                "detail_text": (record.detail_text or "")
                + "\n超时自动释放计算锁",
                "finished_at": now(),
            },
        )
        db.commit()

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[StampingPartCostCalcLogVO], int]:
        skip = (page - 1) * size
        rows, total = self.calc_log_repo.paginate(
            db,
            year=year,
            month=month,
            location=location,
            stamping_supplier=stamping_supplier,
            skip=skip,
            limit=size,
        )
        return [StampingPartCostCalcLogVO.model_validate(r) for r in rows], total

    def get_calc_log(
        self, db: Session, log_id: int
    ) -> StampingPartCostCalcLogVO | None:
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            return None
        return StampingPartCostCalcLogVO.model_validate(record)

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
