"""计算批次日志读写（历史列表 / detail_text 落库）。"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.steel_price import SteelPriceCalcLogRepository
from app.schemas.vo.steel_price_vo import SteelPriceCalcLogVO
from app.services.steel_price.calc.models import SteelPriceCalcResult


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
