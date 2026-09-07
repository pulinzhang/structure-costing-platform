"""焊接费计算日志：锁、过期释放、CRUD。"""

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
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom import BomWeldingFeeCalcLog
from app.repositories.bom.welding_fee_calc_log_repository import (
    BomWeldingFeeCalcLogRepository,
)
from app.schemas.common import DeletedCountVO
from app.schemas.dto.bom_welding_fee_dto import (
    BomWeldingFeeCalcDTO,
    BomWeldingFeeCalcLogCreate,
    BomWeldingFeeCalcLogPatch,
)
from app.schemas.vo.bom_welding_fee_vo import (
    BomWeldingFeeCalcLogVO,
    BomWeldingFeeCalcResultVO,
)

STATUS_PROCESSING = "processing"
STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"

STALE_PROCESSING_SECONDS = 2 * 60 * 60
DUPLICATE_SCOPE_CALC_MESSAGE = "当前年度/基地/项目/版本正在计算中，请勿重复提交。"

logger = logging.getLogger("service.bom.welding_fee.calc.log")


class DuplicateScopeCalcError(BusinessException):
    """同一计算范围已有进行中的任务。"""

    def __init__(self, message: str = DUPLICATE_SCOPE_CALC_MESSAGE) -> None:
        super().__init__(message=message, code=409)


class BomWeldingFeeCalcLogService:
    """计算日志与并发锁。"""

    def __init__(
        self,
        calc_log_repo: BomWeldingFeeCalcLogRepository | None = None,
    ) -> None:
        self.calc_log_repo = calc_log_repo or BomWeldingFeeCalcLogRepository()

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
        dto: BomWeldingFeeCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> BomWeldingFeeCalcLog:
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
                BomWeldingFeeCalcLogCreate(
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
        data: BomWeldingFeeCalcLogPatch,
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
        with contextlib.suppress(Exception):
            db.rollback()
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
    ) -> tuple[list[BomWeldingFeeCalcLogVO], int]:
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
        return [BomWeldingFeeCalcLogVO.model_validate(r) for r in rows], total

    def get_calc_log(self, db: Session, log_id: int) -> BomWeldingFeeCalcLogVO:
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            raise NotFoundException("计算日志不存在")
        return BomWeldingFeeCalcLogVO.model_validate(record)

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        """删除计算日志（含 processing，作僵死锁兜底释放）。"""
        record = self.calc_log_repo.get_by_id(db, log_id)
        if record is None:
            raise NotFoundException("计算日志不存在")
        deleted = self.calc_log_repo.delete(db, log_id)
        if not deleted:
            raise NotFoundException("计算日志不存在")
        db.commit()

    def delete_all_logs(self, db: Session) -> DeletedCountVO:
        deleted_count = self.calc_log_repo.delete_all(db)
        db.commit()
        return DeletedCountVO(deleted_count=deleted_count)

    def persist(
        self,
        db: Session,
        *,
        result: BomWeldingFeeCalcResultVO,
        operator_name: str | None = None,
    ) -> int | None:
        """引擎等同步调用未走 begin_processing 时，补写终态历史。"""
        operator = operator_name or "系统"
        started_at = datetime.fromisoformat(result.started_at) if result.started_at else now()
        finished_at = datetime.fromisoformat(result.finished_at) if result.finished_at else now()
        calc_batch_id = result.calc_batch_id or f"bwf-{uuid.uuid4().hex[:16]}"
        try:
            record = self.calc_log_repo.create(
                db,
                BomWeldingFeeCalcLogCreate(
                    calc_batch_id=calc_batch_id,
                    year=result.year,
                    location=result.location,
                    vehicle_model=result.vehicle_model,
                    bom_version=result.bom_version,
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
                BomWeldingFeeCalcLogPatch(
                    status=result.status,
                    l0_count=result.l0_count,
                    created_count=result.created_count,
                    updated_count=result.updated_count,
                    skipped_approved_count=result.skipped_approved_count,
                    failed_count=result.failed_count,
                    missing_price_count=result.missing_price_count,
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
            logger.exception("写入焊接费计算日志失败: batch=%s", calc_batch_id)
            return None
