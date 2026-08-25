"""焊接工艺拆解生成 — 批次日志服务。"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import cast

from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom import (
    BomWeldingProcessBreakdownGenerateLog,
)
from app.repositories.bom.welding_process_breakdown_generate_log_repository import (
    BomWeldingProcessBreakdownGenerateLogRepository,
)
from app.schemas.dto.bom_welding_process_breakdown_dto import (
    BomWeldingProcessBreakdownGenerateLogCreate,
    BomWeldingProcessBreakdownGenerateLogPatch,
)
from app.schemas.vo.bom_welding_process_breakdown_vo import (
    BomWeldingProcessBreakdownGenerateLogVO,
    BomWeldingProcessBreakdownGenerateResultVO,
)

logger = logging.getLogger("service.bom.welding_process_breakdown.generate_log")

STATUS_PROCESSING = "processing"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STALE_PROCESSING_SECONDS = 2 * 3600
DUPLICATE_SCOPE_GENERATE_MESSAGE = "当前范围正在拆解中，请勿重复提交。"


class DuplicateScopeGenerateError(BusinessException):
    """同一基地+项目+版本已有 processing 锁。"""

    def __init__(self, message: str = DUPLICATE_SCOPE_GENERATE_MESSAGE) -> None:
        super().__init__(message=message, code=409)


class BomWeldingProcessBreakdownGenerateLogService:
    """拆解生成批次日志。"""

    def __init__(self) -> None:
        self.repository = BomWeldingProcessBreakdownGenerateLogRepository()

    def _ensure_processing_lock_index(self, db: Session) -> None:
        """DDL 用独立连接；commit 在 Service（不进业务 Session）。"""
        if self.repository.is_processing_lock_index_ensured():
            return
        bind = cast(Engine, db.get_bind())
        with bind.connect() as conn:
            self.repository.apply_processing_lock_index(conn)
            conn.commit()
        self.repository.mark_processing_lock_index_ensured()

    def list_logs(
        self,
        db: Session,
        *,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[BomWeldingProcessBreakdownGenerateLogVO], int]:
        skip = (page - 1) * size
        records, total = self.repository.paginate(
            db,
            location=location.strip() if location else None,
            vehicle_model=vehicle_model.strip() if vehicle_model else None,
            bom_version=bom_version.strip() if bom_version else None,
            skip=skip,
            limit=size,
        )
        return [
            BomWeldingProcessBreakdownGenerateLogVO.model_validate(r) for r in records
        ], total

    def get_log(
        self, db: Session, log_id: int
    ) -> BomWeldingProcessBreakdownGenerateLogVO:
        record = self.repository.get_by_id(db, log_id)
        if record is None:
            raise NotFoundException("拆解记录不存在")
        return BomWeldingProcessBreakdownGenerateLogVO.model_validate(record)

    def delete_log(self, db: Session, log_id: int) -> None:
        """删除拆解日志（含 processing，作僵死锁兜底释放）。"""
        record = self.repository.get_by_id(db, log_id)
        if record is None:
            raise NotFoundException("拆解记录不存在")
        deleted = self.repository.delete(db, log_id)
        if not deleted:
            raise NotFoundException("拆解记录不存在")
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("删除拆解日志失败: id=%s", log_id)
            raise

    def is_scope_processing(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> bool:
        self._expire_stale_processing(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        return (
            self.repository.find_processing(
                db,
                location=location,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
            )
            is not None
        )

    def begin_processing(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
        customer_name: str | None = None,
        operator_id: int | None = None,
        operator_name: str | None = None,
    ) -> BomWeldingProcessBreakdownGenerateLog:
        self._ensure_processing_lock_index(db)
        self._expire_stale_processing(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        existing = self.repository.find_processing(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        if existing is not None:
            raise DuplicateScopeGenerateError(DUPLICATE_SCOPE_GENERATE_MESSAGE)

        started_at = now()
        calc_batch_id = f"wpb-gen-{uuid.uuid4().hex[:16]}"
        try:
            record = self.repository.create(
                db,
                BomWeldingProcessBreakdownGenerateLogCreate(
                    calc_batch_id=calc_batch_id,
                    location=location,
                    vehicle_model=vehicle_model,
                    bom_version=bom_version,
                    customer_name=customer_name,
                    snapshot_id=None,
                    status=STATUS_PROCESSING,
                    node_count=0,
                    line_count=0,
                    detail_text="拆解进行中...",
                    started_at=started_at,
                    finished_at=None,
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
            raise DuplicateScopeGenerateError(DUPLICATE_SCOPE_GENERATE_MESSAGE) from error

    def finalize(
        self,
        db: Session,
        *,
        log_id: int,
        result: BomWeldingProcessBreakdownGenerateResultVO,
        finished_at: datetime,
    ) -> int | None:
        payload: BomWeldingProcessBreakdownGenerateLogPatch = {
            "status": result.status or STATUS_SUCCESS,
            "customer_name": result.customer_name,
            "snapshot_id": result.snapshot_id,
            "node_count": result.node_count,
            "line_count": result.line_count,
            "detail_text": result.detail_text or "",
            "finished_at": finished_at,
        }
        try:
            existing = self.repository.get_by_id(db, log_id)
            if existing is not None and existing.operator_name:
                payload["updated_by"] = existing.operator_name
            record = self.repository.update(db, log_id, payload)
            if record is None:
                return None
            db.commit()
            db.refresh(record)
            return record.id
        except Exception:
            db.rollback()
            logger.exception("更新拆解日志失败: log_id=%s", log_id)
            return None

    def mark_failed(
        self,
        db: Session,
        *,
        log_id: int,
        message: str,
        detail_text: str | None = None,
    ) -> None:
        """异常路径：释放 processing 锁为 failed（先 rollback 清脏事务）。"""
        try:
            db.rollback()
        except Exception:
            pass
        finished_at = now()
        payload: BomWeldingProcessBreakdownGenerateLogPatch = {
            "status": STATUS_FAILED,
            "finished_at": finished_at,
            "detail_text": detail_text or message,
        }
        try:
            existing = self.repository.get_by_id(db, log_id)
            if existing is not None and existing.operator_name:
                payload["updated_by"] = existing.operator_name
            elif existing is not None and existing.created_by:
                payload["updated_by"] = existing.created_by
            else:
                payload["updated_by"] = "系统"
            self.repository.update(db, log_id, payload)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("标记拆解日志失败态异常: log_id=%s", log_id)

    def _expire_stale_processing(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        bom_version: str,
    ) -> None:
        record = self.repository.find_processing(
            db,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        if record is None or record.started_at is None:
            return
        age = now() - record.started_at
        if age < timedelta(seconds=STALE_PROCESSING_SECONDS):
            return
        hours = STALE_PROCESSING_SECONDS // 3600
        self.mark_failed(
            db,
            log_id=record.id,
            message=f"拆解超时（超过 {hours} 小时），已自动释放锁",
            detail_text=(
                f"僵死锁回收：processing 超过 {hours} 小时未结束，"
                f"started_at={record.started_at.isoformat(timespec='seconds')}"
            ),
        )
