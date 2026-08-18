"""废料月度销售价格 CRUD（按月矩阵）。"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.scrap_price_locations import (
    SCRAP_PRICE_LOCATION_COUNT,
    SCRAP_PRICE_LOCATIONS,
)
from app.models.yishiyiyi import StampingScrapPrice
from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)
from app.schemas.dto.stamping_scrap_price_dto import (
    ScrapPriceWrite,
    StampingScrapPriceCopyMonth,
    StampingScrapPriceMonthSaveDTO,
)
from app.schemas.vo.stamping_scrap_price_vo import (
    StampingScrapPriceCopyMonthResponse,
    StampingScrapPriceFilterOptionsVO,
    StampingScrapPriceMonthRowVO,
    StampingScrapPriceMonthSheetVO,
    StampingScrapPriceMonthSummaryVO,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.stamping_scrap_price.crud")


class StampingScrapPriceCrudService:
    """废料销售价格：整月取数 / 提交 / 复制 / 删除。"""

    def __init__(self) -> None:
        self.repository = StampingScrapPriceRepository()

    @staticmethod
    def _compute_net_price(
        market_price: Decimal,
        deduction_fee: Decimal,
    ) -> Decimal:
        return market_price - deduction_fee

    def _build_month_sheet(
        self,
        year: int,
        month: int,
        records: list[StampingScrapPrice],
    ) -> StampingScrapPriceMonthSheetVO:
        by_location = {r.location: r for r in records}
        items: List[StampingScrapPriceMonthRowVO] = []
        for location in SCRAP_PRICE_LOCATIONS:
            record = by_location.get(location)
            if record:
                items.append(StampingScrapPriceMonthRowVO.model_validate(record))
            else:
                items.append(StampingScrapPriceMonthRowVO(location=location))

        filled_count = sum(1 for item in items if item.id is not None)
        return StampingScrapPriceMonthSheetVO(
            year=year,
            month=month,
            is_saved=filled_count > 0,
            is_complete=filled_count == SCRAP_PRICE_LOCATION_COUNT,
            filled_count=filled_count,
            locations=list(SCRAP_PRICE_LOCATIONS),
            items=items,
        )

    def get_month_sheet(
        self,
        db: Session,
        year: int,
        month: int,
    ) -> StampingScrapPriceMonthSheetVO:
        records = self.repository.list_by_year_month(db, year, month)
        return self._build_month_sheet(year, month, records)

    def list_month_summaries(
        self,
        db: Session,
        year: Optional[int] = None,
    ) -> List[StampingScrapPriceMonthSummaryVO]:
        rows = self.repository.list_month_summaries(db, year=year)
        return [
            StampingScrapPriceMonthSummaryVO(
                year=year_value,
                month=month_value,
                filled_count=filled_count,
                is_complete=filled_count >= SCRAP_PRICE_LOCATION_COUNT,
                updated_at=updated_at,
            )
            for year_value, month_value, filled_count, updated_at in rows
        ]

    def get_filter_options(self, db: Session) -> StampingScrapPriceFilterOptionsVO:
        options = self.repository.get_filter_options(db)
        return StampingScrapPriceFilterOptionsVO(
            years=options.years,
            locations=list(SCRAP_PRICE_LOCATIONS),
        )

    def save_month(
        self,
        db: Session,
        data: StampingScrapPriceMonthSaveDTO,
        current_user: UserVO,
    ) -> Tuple[Optional[StampingScrapPriceMonthSheetVO], Optional[str]]:
        try:
            audit = audit_create(current_user)
            payloads: list[ScrapPriceWrite] = []
            for row in data.items:
                payloads.append(
                    ScrapPriceWrite(
                        location=row.location,
                        year=data.year,
                        month=data.month,
                        market_price=row.market_price,
                        deduction_fee=row.deduction_fee,
                        net_price=self._compute_net_price(
                            row.market_price,
                            row.deduction_fee,
                        ),
                        remark=row.remark,
                        created_by=audit["created_by"],
                        updated_by=audit["updated_by"],
                    )
                )

            records = self.repository.replace_year_month(
                db,
                data.year,
                data.month,
                payloads,
            )
            sheet = self._build_month_sheet(data.year, data.month, records)
            return sheet, None
        except Exception as exc:
            db.rollback()
            logger.error("整月保存废料销售价失败: %s", exc)
            return None, str(exc)

    def delete_month(
        self,
        db: Session,
        year: int,
        month: int,
    ) -> Tuple[int, Optional[str]]:
        count = self.repository.delete_by_year_month(db, year, month)
        if count == 0:
            return 0, f"{year}-{month:02d} 没有可删除的数据"
        return count, None

    def copy_month(
        self,
        db: Session,
        body: StampingScrapPriceCopyMonth,
        current_user: UserVO,
    ) -> Tuple[Optional[StampingScrapPriceCopyMonthResponse], Optional[str]]:
        if (
            body.source_year == body.target_year
            and body.source_month == body.target_month
        ):
            return None, "源年月与目标年月不能相同"

        source_records = self.repository.list_by_year_month(
            db,
            body.source_year,
            body.source_month,
        )
        if not source_records:
            return None, (
                f"源年月 {body.source_year}-{body.source_month:02d} 没有数据"
            )

        by_location = {r.location: r for r in source_records}
        missing = [name for name in SCRAP_PRICE_LOCATIONS if name not in by_location]
        if missing:
            return None, (
                f"源月数据不完整，缺少: {', '.join(missing)}；请先补全源月再复制"
            )

        audit = audit_create(current_user)
        payloads: list[ScrapPriceWrite] = []
        for location in SCRAP_PRICE_LOCATIONS:
            source = by_location[location]
            payloads.append(
                ScrapPriceWrite(
                    location=location,
                    year=body.target_year,
                    month=body.target_month,
                    market_price=source.market_price,
                    deduction_fee=source.deduction_fee,
                    net_price=source.net_price,
                    remark=source.remark,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                )
            )

        try:
            records = self.repository.replace_year_month(
                db,
                body.target_year,
                body.target_month,
                payloads,
            )
            return (
                StampingScrapPriceCopyMonthResponse(
                    source_year=body.source_year,
                    source_month=body.source_month,
                    target_year=body.target_year,
                    target_month=body.target_month,
                    created_count=len(records),
                ),
                None,
            )
        except Exception as exc:
            db.rollback()
            logger.error("跨月复制废料销售价失败: %s", exc)
            return None, str(exc)
