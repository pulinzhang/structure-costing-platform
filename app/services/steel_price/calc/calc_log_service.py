"""计算批次日志读写（历史列表 / detail_text 落库）。"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.steel_price_calc_log import SteelPriceCalcLog
from app.repositories.steel_price import SteelPriceCalcLogRepository
from app.schemas.vo.steel_price_vo import SteelPriceCalcLogVO
from app.services.steel_price.calc.models import SteelPriceCalcResult
from app.services.steel_price.calc.status import (
    DUPLICATE_PERIOD_CALC_MESSAGE,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STALE_PROCESSING_SECONDS,
    DuplicatePeriodCalcError,
)


logger = logging.getLogger("service.steel_price.calc.log")


class CalcLogService:
    """钢价计算批次日志。"""

    def __init__(self) -> None:
        self.repository = SteelPriceCalcLogRepository()

    def list_logs(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[SteelPriceCalcLogVO], int]:
        skip = (page - 1) * size
        records, total = self.repository.paginate(
            db,
            year=year,
            month=month,
            location=location.strip() if location else None,
            skip=skip,
            limit=size,
        )
        return [SteelPriceCalcLogVO.model_validate(r) for r in records], total

    def get_log(self, db: Session, log_id: int) -> SteelPriceCalcLogVO | None:
        record = self.repository.get_by_id(db, log_id)
        if record is None:
            return None
        return SteelPriceCalcLogVO.model_validate(record)

    def delete_log(self, db: Session, log_id: int) -> bool:
        record = self.repository.get_by_id(db, log_id)
        if record is None:
            return False
        if record.status == STATUS_PROCESSING:
            raise ValueError("计算进行中，无法删除该记录")
        deleted = self.repository.delete(db, log_id)
        if not deleted:
            return False
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("删除计算日志失败: id=%s", log_id)
            raise
        return True

    def is_period_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
    ) -> bool:
        """期别是否正在计算（会顺带回收超时僵死锁）。"""
        self._expire_stale_processing(db, year=year, month=month, location=location)
        return (
            self.repository.find_processing(
                db, year=year, month=month, location=location
            )
            is not None
        )

    def begin_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
    ) -> SteelPriceCalcLog:
        """
        为期别写入 processing 锁行。

        同一 year+month+location 已有 processing 时抛出 DuplicatePeriodCalcError。
        """
        self.repository.ensure_processing_lock_index(db)
        self._expire_stale_processing(db, year=year, month=month, location=location)

        existing = self.repository.find_processing(
            db, year=year, month=month, location=location
        )
        if existing is not None:
            raise DuplicatePeriodCalcError(DUPLICATE_PERIOD_CALC_MESSAGE)

        started_at = datetime.now()
        calc_batch_id = f"calc-{uuid.uuid4().hex[:16]}"
        try:
            record = self.repository.create(
                db,
                {
                    "calc_batch_id": calc_batch_id,
                    "year": year,
                    "month": month,
                    "location": location,
                    "stamping_supplier": stamping_supplier,
                    "vehicle_model": vehicle_model,
                    "status": STATUS_PROCESSING,
                    "material_count": 0,
                    "enriched_count": 0,
                    "no_base_count": 0,
                    "created_count": 0,
                    "updated_count": 0,
                    "skipped_approved_count": 0,
                    "failed_count": 0,
                    "detail_text": "计算进行中...",
                    "started_at": started_at,
                    "finished_at": None,
                },
            )
            db.commit()
            db.refresh(record)
            return record
        except IntegrityError as error:
            db.rollback()
            logger.warning(
                "期别计算锁冲突: year=%s month=%s location=%s",
                year,
                month,
                location,
            )
            raise DuplicatePeriodCalcError(DUPLICATE_PERIOD_CALC_MESSAGE) from error

    def finalize(
        self,
        db: Session,
        *,
        log_id: int,
        result: SteelPriceCalcResult,
        finished_at: datetime,
    ) -> int | None:
        """将 processing 行更新为终态；若行不存在则回退创建。"""
        payload = {
            "status": result.status,
            "material_count": result.material_count,
            "enriched_count": result.enriched_count,
            "no_base_count": result.no_base_count,
            "created_count": result.created_count,
            "updated_count": result.updated_count,
            "skipped_approved_count": result.skipped_approved_count,
            "failed_count": result.failed_count,
            "detail_text": result.detail_text or "",
            "finished_at": finished_at,
        }
        try:
            record = self.repository.update(db, log_id, payload)
            if record is None:
                logger.warning(
                    "finalize 未找到日志行，回退创建: log_id=%s batch=%s",
                    log_id,
                    result.calc_batch_id,
                )
                return self.persist(
                    db,
                    result=result,
                    started_at=datetime.fromisoformat(result.started_at)
                    if result.started_at
                    else finished_at,
                    finished_at=finished_at,
                )
            db.commit()
            db.refresh(record)
            return record.id
        except Exception:
            db.rollback()
            logger.exception(
                "更新计算日志失败: log_id=%s batch=%s", log_id, result.calc_batch_id
            )
            return None

    def mark_failed(
        self,
        db: Session,
        *,
        log_id: int,
        message: str,
        detail_text: str | None = None,
    ) -> None:
        """异常路径：释放 processing 锁为 failed。"""
        finished_at = datetime.now()
        payload = {
            "status": STATUS_FAILED,
            "finished_at": finished_at,
            "detail_text": detail_text or message,
        }
        try:
            record = self.repository.update(db, log_id, payload)
            if record is None:
                return
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("标记计算日志失败态异常: log_id=%s", log_id)

    def persist(
        self,
        db: Session,
        *,
        result: SteelPriceCalcResult,
        started_at: datetime,
        finished_at: datetime,
    ) -> int | None:
        if result.year is None or result.month is None:
            logger.error(
                "写入计算日志失败: batch=%s 缺少 year/month", result.calc_batch_id
            )
            return None
        try:
            record = self.repository.create(
                db,
                {
                    "calc_batch_id": result.calc_batch_id,
                    "year": int(result.year),
                    "month": int(result.month),
                    "location": result.location or "",
                    "stamping_supplier": result.stamping_supplier,
                    "vehicle_model": result.vehicle_model,
                    "status": result.status,
                    "material_count": result.material_count,
                    "enriched_count": result.enriched_count,
                    "no_base_count": result.no_base_count,
                    "created_count": result.created_count,
                    "updated_count": result.updated_count,
                    "skipped_approved_count": result.skipped_approved_count,
                    "failed_count": result.failed_count,
                    "detail_text": result.detail_text or "",
                    "started_at": started_at,
                    "finished_at": finished_at,
                },
            )
            db.commit()
            db.refresh(record)
            return record.id
        except Exception as error:
            db.rollback()
            logger.exception(
                "写入计算日志失败: batch=%s error=%s", result.calc_batch_id, error
            )
            return None

    def _expire_stale_processing(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
    ) -> None:
        record = self.repository.find_processing(
            db, year=year, month=month, location=location
        )
        if record is None or record.started_at is None:
            return
        age = datetime.now() - record.started_at
        if age < timedelta(seconds=STALE_PROCESSING_SECONDS):
            return
        finished_at = datetime.now()
        hours = STALE_PROCESSING_SECONDS // 3600
        self.repository.update(
            db,
            record.id,
            {
                "status": STATUS_FAILED,
                "finished_at": finished_at,
                "detail_text": (
                    f"{record.detail_text or ''}\n\n"
                    f"[系统] processing 超过 {hours} 小时未完成，已自动释放期别锁"
                ).strip(),
            },
        )
        try:
            db.commit()
            logger.warning(
                "回收僵死计算锁: id=%s year=%s month=%s location=%s age=%ss",
                record.id,
                year,
                month,
                location,
                int(age.total_seconds()),
            )
        except Exception:
            db.rollback()
            logger.exception("回收僵死计算锁失败: id=%s", record.id)
