"""成品月核价 — 计算日志与 scope 锁。"""

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
from app.models.costing.assembly_cost_calc_log import AssemblyCostCalcLog
from app.repositories.costing.assembly_cost.assembly_cost_calc_log_repository import (
    AssemblyCostCalcLogRepository,
)
from app.schemas.common import DeletedCountVO
from app.schemas.dto.assembly_cost_dto import AssemblyCostCalcDTO
from app.schemas.vo.assembly_cost_vo import (
    AssemblyCostCalcCardTraceVO,
    AssemblyCostCalcLogVO,
)
from app.services.costing.assembly_cost.calc.process_log import parse_card_traces

STATUS_PROCESSING = "processing"
STATUS_SUCCESS = "success"
STATUS_PARTIAL = "partial"
STATUS_FAILED = "failed"

STALE_PROCESSING_SECONDS = 2 * 60 * 60
DUPLICATE_SCOPE_CALC_MESSAGE = "当前年度/月份/基地/项目/版本正在计算中，请勿重复提交。"
SCOPE_REQUIRED_MESSAGE = "须选定年度、月份、基地、项目、BOM 版本。"
_DUPLICATE_LOCK_RELEASE_MESSAGE = "重复 processing 锁已释放，以便建立并发唯一索引"

logger = logging.getLogger("service.costing.assembly_cost.calc.log")


class DuplicateScopeCalcError(BusinessException):
    """同一计算范围已有进行中的任务。"""

    def __init__(self, message: str = DUPLICATE_SCOPE_CALC_MESSAGE) -> None:
        super().__init__(message=message, code=409)


class AssemblyCostCalcLogService:
    def __init__(
        self,
        calc_log_repo: AssemblyCostCalcLogRepository | None = None,
    ) -> None:
        self.calc_log_repo = calc_log_repo or AssemblyCostCalcLogRepository()

    def _ensure_processing_lock_index(self, db: Session) -> None:
        """DDL 用独立连接；commit 在 Service（不进业务 Session）。"""
        if self.calc_log_repo.is_processing_lock_index_ensured():
            return
        bind = cast(Engine, db.get_bind())
        with bind.connect() as conn:
            self.calc_log_repo.apply_processing_lock_index(conn)
            conn.commit()
        self.calc_log_repo.mark_processing_lock_index_ensured()

    def _fail_older_duplicate_processing(self, db: Session) -> int:
        """同一 scope 只保留 id 最大的 processing，其余标 failed。"""
        rows = self.calc_log_repo.list_processing(db)
        latest_by_scope: dict[tuple[int, int, str, str, str], AssemblyCostCalcLog] = {}
        extras: list[AssemblyCostCalcLog] = []
        for row in rows:
            key = (row.year, row.month, row.location, row.vehicle_model, row.bom_version)
            keep = latest_by_scope.get(key)
            if keep is None:
                latest_by_scope[key] = row
                continue
            if row.id > keep.id:
                extras.append(keep)
                latest_by_scope[key] = row
            else:
                extras.append(row)
        if not extras:
            return 0
        finished_at = now()
        for row in extras:
            row.status = STATUS_FAILED
            row.message = _DUPLICATE_LOCK_RELEASE_MESSAGE
            row.finished_at = finished_at
        db.flush()
        logger.warning("释放重复 processing 锁: count=%s", len(extras))
        return len(extras)

    def expire_stale_processing(self, db: Session) -> int:
        cutoff = now() - timedelta(seconds=STALE_PROCESSING_SECONDS)
        return self.calc_log_repo.expire_stale_processing(
            db,
            older_than=cutoff,
            message="计算超时未完成，已自动释放锁",
        )

    def begin_processing(
        self,
        db: Session,
        dto: AssemblyCostCalcDTO,
        *,
        operator_id: int | None,
        operator_name: str | None,
    ) -> AssemblyCostCalcLog:
        location = dto.location.strip()
        vehicle_model = dto.vehicle_model.strip()
        bom_version = dto.bom_version.strip()
        self.expire_stale_processing(db)
        if not self.calc_log_repo.is_processing_lock_index_ensured():
            self._fail_older_duplicate_processing(db)
            db.commit()
        self._ensure_processing_lock_index(db)
        existing = self.calc_log_repo.get_processing_by_scope(
            db,
            year=dto.year,
            month=dto.month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        if existing is not None:
            raise DuplicateScopeCalcError(DUPLICATE_SCOPE_CALC_MESSAGE)

        row = AssemblyCostCalcLog(
            year=dto.year,
            month=dto.month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            calc_batch_id=uuid.uuid4().hex,
            status=STATUS_PROCESSING,
            message="计算中…",
            detail_text="计算中…\n",
            started_at=now(),
            operator_id=operator_id,
            operator_name=operator_name,
            created_by=operator_name or "system",
            updated_by=operator_name or "system",
        )
        try:
            self.calc_log_repo.create(db, row)
            db.commit()
            db.refresh(row)
            return row
        except IntegrityError as error:
            db.rollback()
            raise DuplicateScopeCalcError(DUPLICATE_SCOPE_CALC_MESSAGE) from error

    def mark_log_failed(self, db: Session, *, log_id: int, detail_text: str) -> None:
        """异常路径：释放 processing 锁为 failed（先 rollback 清脏事务）。"""
        with contextlib.suppress(Exception):
            db.rollback()
        row = self.calc_log_repo.get_by_id(db, log_id)
        if row is None:
            return
        row.status = STATUS_FAILED
        row.message = detail_text
        row.detail_text = detail_text
        row.finished_at = now()
        db.commit()

    def finalize(
        self,
        db: Session,
        *,
        log_id: int,
        status: str,
        message: str | None,
        subject_total: int,
        ok_count: int,
        partial_count: int,
        failed_count: int,
        skipped_approved_count: int,
        detail_text: str | None = None,
        detail_json: str | None = None,
    ) -> None:
        row = self.calc_log_repo.get_by_id(db, log_id)
        if row is None:
            return
        row.status = status
        row.message = message
        row.subject_total = subject_total
        row.ok_count = ok_count
        row.partial_count = partial_count
        row.failed_count = failed_count
        row.skipped_approved_count = skipped_approved_count
        if detail_text is not None:
            row.detail_text = detail_text
        if detail_json is not None:
            row.detail_json = detail_json
        row.finished_at = now()
        db.commit()

    def persist(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        vehicle_model: str,
        bom_version: str,
        status: str,
        message: str | None,
        subject_total: int,
        ok_count: int,
        partial_count: int,
        failed_count: int,
        skipped_approved_count: int,
        detail_text: str,
        detail_json: str | None,
        operator_id: int | None,
        operator_name: str | None,
        calc_batch_id: str | None = None,
    ) -> int | None:
        """引擎等同步调用未走 begin_processing 时，补写终态历史。"""
        operator = (operator_name or "").strip() or "系统"
        finished_at = now()
        row = AssemblyCostCalcLog(
            year=year,
            month=month,
            location=location.strip(),
            vehicle_model=vehicle_model.strip(),
            bom_version=bom_version.strip(),
            calc_batch_id=calc_batch_id or uuid.uuid4().hex,
            status=status,
            message=message,
            subject_total=subject_total,
            ok_count=ok_count,
            partial_count=partial_count,
            failed_count=failed_count,
            skipped_approved_count=skipped_approved_count,
            detail_text=detail_text,
            detail_json=detail_json,
            started_at=finished_at,
            finished_at=finished_at,
            operator_id=operator_id,
            operator_name=operator,
            created_by=operator,
            updated_by=operator,
        )
        try:
            self.calc_log_repo.create(db, row)
            db.commit()
            db.refresh(row)
            return row.id
        except Exception:
            db.rollback()
            logger.exception("写入总成核价计算日志失败: batch=%s", row.calc_batch_id)
            return None

    def list_calc_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AssemblyCostCalcLogVO], int]:
        rows, total = self.calc_log_repo.paginate(
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            skip=skip,
            limit=limit,
        )
        return [AssemblyCostCalcLogVO.model_validate(r) for r in rows], total

    def get_calc_log(self, db: Session, log_id: int) -> AssemblyCostCalcLogVO:
        row = self.calc_log_repo.get_by_id(db, log_id)
        if row is None:
            raise NotFoundException("计算日志不存在")
        vo = AssemblyCostCalcLogVO.model_validate(row)
        vo.cards = [
            AssemblyCostCalcCardTraceVO.model_validate(card)
            for card in parse_card_traces(row.detail_json)
        ]
        return vo

    def delete_calc_log(self, db: Session, log_id: int) -> None:
        ok = self.calc_log_repo.delete(db, log_id)
        if not ok:
            raise NotFoundException("计算日志不存在")
        db.commit()

    def delete_all_logs(self, db: Session) -> DeletedCountVO:
        deleted_count = self.calc_log_repo.delete_all(db)
        db.commit()
        return DeletedCountVO(deleted_count=deleted_count)
