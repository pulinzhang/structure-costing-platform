"""
冲压废料月度销售价格 Repository
仅负责查询构建与 CRUD，不含业务判断
"""

import logging
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.common.types.repository_types import ScrapPriceFilterOptions
from app.models.yishiyiyi import StampingScrapPrice
from app.repositories.persist import model_from_payload
from app.schemas.dto.stamping_scrap_price_dto import ScrapPriceWrite

logger = logging.getLogger("repository.stamping_scrap_price")


class StampingScrapPriceRepository:
    """废料销售价格数据访问"""

    def list_by_year_month(
        self,
        db: Session,
        year: int,
        month: int,
    ) -> list[StampingScrapPrice]:
        return (
            db.query(StampingScrapPrice)
            .filter(
                StampingScrapPrice.year == year,
                StampingScrapPrice.month == month,
            )
            .all()
        )

    def get_by_location_year_month(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        month: int,
    ) -> StampingScrapPrice | None:
        return (
            db.query(StampingScrapPrice)
            .filter(
                StampingScrapPrice.location == location,
                StampingScrapPrice.year == year,
                StampingScrapPrice.month == month,
            )
            .first()
        )

    def list_by_ids(self, db: Session, record_ids: list[int]) -> list[StampingScrapPrice]:
        """按主键批量查询。"""
        if not record_ids:
            return []
        return db.query(StampingScrapPrice).filter(StampingScrapPrice.id.in_(record_ids)).all()

    def list_by_year(
        self,
        db: Session,
        year: int,
    ) -> list[StampingScrapPrice]:
        return (
            db.query(StampingScrapPrice)
            .filter(StampingScrapPrice.year == year)
            .order_by(StampingScrapPrice.month, StampingScrapPrice.location)
            .all()
        )

    def list_years_asc(self, db: Session) -> list[int]:
        return [
            row[0]
            for row in (
                db.query(StampingScrapPrice.year)
                .distinct()
                .order_by(StampingScrapPrice.year.asc())
                .all()
            )
        ]

    def list_month_summaries(
        self,
        db: Session,
        year: int | None = None,
    ) -> list[tuple[int, int, int, datetime | None]]:
        """
        按年月汇总：[(year, month, filled_count, max_updated_at), ...]
        按 year desc, month desc 排序。
        """
        query = db.query(
            StampingScrapPrice.year,
            StampingScrapPrice.month,
            func.count(StampingScrapPrice.id),
            func.max(StampingScrapPrice.updated_at),
        )
        if year is not None:
            query = query.filter(StampingScrapPrice.year == year)

        rows = (
            query.group_by(StampingScrapPrice.year, StampingScrapPrice.month)
            .order_by(
                StampingScrapPrice.year.desc(),
                StampingScrapPrice.month.desc(),
            )
            .all()
        )
        return [(r[0], r[1], int(r[2]), r[3]) for r in rows]

    def get_filter_options(self, db: Session) -> ScrapPriceFilterOptions:
        years = [
            row[0]
            for row in (
                db.query(StampingScrapPrice.year)
                .distinct()
                .order_by(StampingScrapPrice.year.desc())
                .all()
            )
        ]
        return {"years": years}

    def replace_year_month(
        self,
        db: Session,
        year: int,
        month: int,
        rows: list[ScrapPriceWrite],
    ) -> list[StampingScrapPrice]:
        """同一事务内：删掉该月旧数据，再整月写入。"""
        db.query(StampingScrapPrice).filter(
            StampingScrapPrice.year == year,
            StampingScrapPrice.month == month,
        ).delete(synchronize_session=False)

        records = [model_from_payload(StampingScrapPrice, row) for row in rows]
        db.add_all(records)
        db.flush()
        for record in records:
            db.refresh(record)

        logger.info(
            "整月保存废料销售价: year=%s month=%s count=%s",
            year,
            month,
            len(records),
        )
        return records

    def delete_by_year_month(self, db: Session, year: int, month: int) -> int:
        count = (
            db.query(StampingScrapPrice)
            .filter(
                StampingScrapPrice.year == year,
                StampingScrapPrice.month == month,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        logger.info("删除 %s-%s 废料销售价: %s 条", year, month, count)
        return count
