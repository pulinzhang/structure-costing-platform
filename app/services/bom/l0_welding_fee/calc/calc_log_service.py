"""焊接费计算日志：锁、过期释放、CRUD。"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import cast

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException
from app.models.bom import BomL0WeldingFeeCalcLog
from app.repositories.bom.l0_welding_fee_calc_log_repository import (
    BomL0WeldingFeeCalcLogRepository,
)
from app.schemas.dto.bom_l0_welding_fee_dto import (
    BomL0WeldingFeeCalcDTO,
    BomL0WeldingFeeCalcLogCreate,
    BomL0WeldingFeeCalcLogPatch,
)
from app.schemas.vo.bom_l0_welding_fee_vo import BomL0WeldingFeeCalcLogVO

STATUS_PROCESSING = "processing"
STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"

STALE_PROCESSING_SECONDS = 2 * 60 * 60
DUPLICATE_SCOPE_CALC_MESSAGE = "当前年度/基地/车型/版本正在计算中，请勿重复提交。"


class DuplicateScopeCalcError(Exception):
    """同一计算范围已有进行中的任务。"""


class BomL0WeldingFeeCalcLogService:
    """计算日志与并发锁。"""

    def __init__(
        self,
        calc_log_repo: BomL0WeldingFeeCalcLogRepository | None = None,
    ) -> None:
        self.calc_log_repo = calc_log_repo or BomL0WeldingFeeCalcLogRepository()

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
        dto: BomL0WeldingFeeCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> BomL0WeldingFeeCalcLog:
        location = dto.location.strip()
        vehicle_model = dto.vehicle_model.strip()
        bom_version = dto.bom_version.strip()
        self._ensure_processing_lock_index(db)
        self.expire_stale_processing(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        existing = self.calc_log_repo.find_processing(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        if existing is not None:
            raise DuplicateScopeCalcError(DUPLICATE_SCOPE_CALC_MESSAGE)

        started_at = now()
        calc_batch_id = f"bwf-{uuid.uuid4().hex[:16]}"
        try:
            record = self.calc_log_repo.create(
                db,
                BomL0WeldingFeeCalcLogCreate(
                    calc_batch_id=calc_batch_id,
                    year=dto.year,
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
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

    def finalize(
        self,
        db: Session,
        *,
        log_id: int,
        data: BomL0WeldingFeeCalcLogPatch,
    ) -> None:
        self.calc_log_repo.update(db, log_id, data)
        db.commit()

    def mark_failed(
        self,
        db: Session,
        *,
        log_id: int,
        detail_text: str,
    ) -> None:
        """异常路径：释放 processing 锁为 failed（先 rollback 清脏事务）。"""
        try:
            db.rollback()
        except Exception:
            pass
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
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> None:
        record = self.calc_log_repo.find_processing(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
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
                "detail_text": (record.detail_text or "") + "\n超时自动释放计算锁",
                "finished_at": now(),
            },
        )
        db.commit()

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[BomL0WeldingFeeCalcLogVO], int]:
        skip = (page - 1) * size
        rows, total = self.calc_log_repo.paginate(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            skip=skip,
            limit=size,
        )
        return [BomL0WeldingFeeCalcLogVO.model_validate(r) for r in rows], total

    def get_calc_log(
        self, db: Session, log_id: int
    ) -> BomL0WeldingFeeCalcLogVO | None:
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            return None
        return BomL0WeldingFeeCalcLogVO.model_validate(record)

    def delete_calc_log(self, db: Session, log_id: int) -> bool:
        """删除计算日志（含 processing，作僵死锁兜底释放）。"""
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            return False
        deleted = self.calc_log_repo.delete(db, log_id)
        if deleted:
            db.commit()
        return deleted
