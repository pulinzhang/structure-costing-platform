"""冲压零件核价计算日志与范围锁。"""

from __future__ import annotations

import contextlib
import logging
import uuid
from datetime import datetime, timedelta
from typing import cast

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import NotFoundException
from app.models.costing import StampingPartCostCalcLog
from app.repositories.costing.stamping_part_cost.stamping_part_cost_calc_log_repository import (
    StampingPartCostCalcLogRepository,
)
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostCalcDTO,
    StampingPartCostCalcLogCreate,
    StampingPartCostCalcLogPatch,
)
from app.schemas.vo.stamping_part_cost_vo import (
    StampingPartCostCalcLogVO,
    StampingPartCostCalcResultVO,
)
from app.services.costing.stamping_part_cost.calc.constants import (
    ALL_SUPPLIERS_LOCK,
    DUPLICATE_SCOPE_CALC_MESSAGE,
    STALE_PROCESSING_SECONDS,
    STATUS_FAILED,
    STATUS_PROCESSING,
)
from app.services.costing.stamping_part_cost.calc.models import DuplicateScopeCalcError
from app.services.costing.stamping_part_cost.calc.scope import require_calc_scope

logger = logging.getLogger("service.stamping_part_cost.calc.log")


class PartCostCalcLogService:
    """计算锁、超时释放与计算日志查询。"""

    def __init__(
        self,
        calc_log_repo: StampingPartCostCalcLogRepository | None = None,
    ) -> None:
        self.calc_log_repo = calc_log_repo or StampingPartCostCalcLogRepository()

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
        dto: StampingPartCostCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> StampingPartCostCalcLog:
        scope = require_calc_scope(dto)
        location = scope.location
        lock_supplier = ALL_SUPPLIERS_LOCK
        self._ensure_processing_lock_index(db)
        self.expire_stale_processing(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            vehicle_model=scope.vehicle_model,
            stamping_supplier=lock_supplier,
        )
        if self._has_conflicting_lock(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            vehicle_model=scope.vehicle_model,
            lock_supplier=lock_supplier,
        ):
            raise DuplicateScopeCalcError(DUPLICATE_SCOPE_CALC_MESSAGE)

        started_at = now()
        calc_batch_id = f"spc-{uuid.uuid4().hex[:16]}"
        try:
            record = self.calc_log_repo.create(
                db,
                StampingPartCostCalcLogCreate(
                    calc_batch_id=calc_batch_id,
                    year=dto.year,
                    month=dto.month,
                    location=location,
                    stamping_supplier=lock_supplier,
                    vehicle_model=scope.vehicle_model,
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
        """异常路径：释放 processing 锁为 failed（先 rollback 清脏事务）。"""
        with contextlib.suppress(Exception):
            db.rollback()
        self.calc_log_repo.update(
            db,
            log_id,
            StampingPartCostCalcLogPatch(
                status=STATUS_FAILED,
                detail_text=detail_text,
                finished_at=now(),
            ),
        )
        db.commit()

    def _lock_conflicts(self, lock_supplier: str, existing_supplier: str) -> bool:
        return ALL_SUPPLIERS_LOCK in (lock_supplier, existing_supplier) or (
            existing_supplier == lock_supplier
        )

    def _has_conflicting_lock(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        lock_supplier: str,
    ) -> bool:
        rows = self.calc_log_repo.list_processing(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
        )
        return any(self._lock_conflicts(lock_supplier, row.stamping_supplier) for row in rows)

    def expire_stale_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        stamping_supplier: str,
    ) -> None:
        changed = False
        for record in self.calc_log_repo.list_processing(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
        ):
            if not self._lock_conflicts(stamping_supplier, record.stamping_supplier):
                continue
            if now() - record.started_at < timedelta(seconds=STALE_PROCESSING_SECONDS):
                continue
            self.calc_log_repo.update(
                db,
                record.id,
                StampingPartCostCalcLogPatch(
                    status=STATUS_FAILED,
                    detail_text=(record.detail_text or "") + "\n超时自动释放计算锁",
                    finished_at=now(),
                ),
            )
            changed = True
        if changed:
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

    def get_calc_log(self, db: Session, log_id: int) -> StampingPartCostCalcLogVO:
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            raise NotFoundException("计算日志不存在")
        return StampingPartCostCalcLogVO.model_validate(record)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        """删除计算日志（含 processing，作僵死锁兜底释放）。"""
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            raise NotFoundException("计算日志不存在")
        deleted = self.calc_log_repo.delete(db, log_id)
        if not deleted:
            raise NotFoundException("计算日志不存在")
        db.commit()

    def persist(
        self,
        db: Session,
        *,
        result: StampingPartCostCalcResultVO,
        operator_name: str | None = None,
    ) -> int | None:
        """引擎等同步调用未走 begin_processing 时，补写终态历史。"""
        operator = operator_name or "系统"
        started_at = datetime.fromisoformat(result.started_at) if result.started_at else now()
        finished_at = datetime.fromisoformat(result.finished_at) if result.finished_at else now()
        calc_batch_id = result.calc_batch_id or f"spc-{uuid.uuid4().hex[:16]}"
        try:
            record = self.calc_log_repo.create(
                db,
                StampingPartCostCalcLogCreate(
                    calc_batch_id=calc_batch_id,
                    year=result.year,
                    month=result.month,
                    location=result.location,
                    stamping_supplier=result.stamping_supplier,
                    vehicle_model=result.vehicle_model,
                    version=result.version,
                    status=result.status,
                    detail_text=result.detail_text or "",
                    started_at=started_at,
                    operator_name=operator,
                    created_by=operator,
                    updated_by=operator,
                ),
            )
            self.calc_log_repo.update(
                db,
                record.id,
                StampingPartCostCalcLogPatch(
                    status=result.status,
                    total_parts=result.total_parts,
                    success_count=result.success_count,
                    failed_count=result.failed_count,
                    skipped_approved_count=result.skipped_approved_count,
                    detail_text=result.detail_text or "",
                    finished_at=finished_at,
                    updated_by=operator,
                ),
            )
            db.commit()
            db.refresh(record)
            return record.id
        except Exception:
            db.rollback()
            logger.exception("写入零件核价计算日志失败: batch=%s", calc_batch_id)
            return None
