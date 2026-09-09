"""废料月度销售价格 CRUD（按月 + 类别矩阵）。"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.scrap_categories import (
    SCRAP_CATEGORY_LABELS,
    require_scrap_category,
)
from app.exceptions.base import BusinessException, NotFoundException
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
from app.services.masterdata.location.location_service import LocationService

logger = logging.getLogger("service.stamping_scrap_price.crud")


class StampingScrapPriceCrudService:
    """废料销售价格：整月取数 / 提交 / 复制 / 删除。"""

    def __init__(self) -> None:
        self.repository = StampingScrapPriceRepository()
        self.location_service = LocationService()

    @staticmethod
    def _compute_net_price(
        market_price: Decimal,
        deduction_fee: Decimal,
    ) -> Decimal:
        return market_price - deduction_fee

    def _enabled_locations(self, db: Session) -> list[str]:
        return self.location_service.list_enabled(db)

    def _build_month_sheet(
        self,
        year: int,
        month: int,
        scrap_category: str,
        enabled: list[str],
        records: list[StampingScrapPrice],
    ) -> StampingScrapPriceMonthSheetVO:
        by_location = {r.location: r for r in records}
        items: list[StampingScrapPriceMonthRowVO] = []
        for location in enabled:
            record = by_location.get(location)
            if record:
                items.append(StampingScrapPriceMonthRowVO.model_validate(record))
            else:
                items.append(
                    StampingScrapPriceMonthRowVO(
                        location=location,
                        scrap_category=scrap_category,
                    )
                )

        filled_count = sum(1 for item in items if item.id is not None)
        required_count = len(enabled)
        return StampingScrapPriceMonthSheetVO(
            year=year,
            month=month,
            scrap_category=scrap_category,
            is_saved=filled_count > 0,
            is_complete=required_count > 0 and filled_count == required_count,
            filled_count=filled_count,
            required_count=required_count,
            locations=list(enabled),
            items=items,
        )

    def get_month_sheet(
        self,
        db: Session,
        year: int,
        month: int,
        scrap_category: str,
    ) -> StampingScrapPriceMonthSheetVO:
        category = require_scrap_category(scrap_category)
        enabled = self._enabled_locations(db)
        records = self.repository.list_by_year_month(db, year, month, scrap_category=category)
        return self._build_month_sheet(year, month, category, enabled, records)

    def list_month_summaries(
        self,
        db: Session,
        year: int | None = None,
        *,
        scrap_category: str,
    ) -> list[StampingScrapPriceMonthSummaryVO]:
        category = require_scrap_category(scrap_category)
        enabled = self._enabled_locations(db)
        required_count = len(enabled)
        rows = self.repository.list_month_summaries(db, year=year, scrap_category=category)
        return [
            StampingScrapPriceMonthSummaryVO(
                year=year_value,
                month=month_value,
                scrap_category=category,
                filled_count=filled_count,
                required_count=required_count,
                is_complete=required_count > 0 and filled_count >= required_count,
                updated_at=updated_at,
            )
            for year_value, month_value, filled_count, updated_at in rows
        ]

    def get_filter_options(self, db: Session) -> StampingScrapPriceFilterOptionsVO:
        options = self.repository.get_filter_options(db)
        return StampingScrapPriceFilterOptionsVO(
            years=options["years"],
            locations=self.location_service.list_registered(db),
        )

    def save_month(
        self,
        db: Session,
        data: StampingScrapPriceMonthSaveDTO,
        current_user: UserVO,
    ) -> StampingScrapPriceMonthSheetVO:
        category = data.scrap_category
        enabled = self._enabled_locations(db)
        if not enabled:
            raise BusinessException("没有已启用基地，请到基地页启用")

        canonical_rows: dict[str, ScrapPriceWrite] = {}
        audit = audit_create(current_user)
        for row in data.items:
            location = self.location_service.require_enabled(db, row.location)
            canonical_rows[location] = ScrapPriceWrite(
                location=location,
                scrap_category=category,
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

        actual = set(canonical_rows)
        expected = set(enabled)
        if actual != expected:
            missing = [name for name in enabled if name not in actual]
            extra = sorted(actual - expected)
            parts: list[str] = []
            if missing:
                parts.append(f"缺少: {', '.join(missing)}")
            if extra:
                parts.append(f"多出: {', '.join(extra)}")
            raise BusinessException("items 必须恰好包含全部已启用基地；" + "；".join(parts))

        payloads = [canonical_rows[name] for name in enabled]
        try:
            records = self.repository.replace_year_month_category(
                db,
                data.year,
                data.month,
                category,
                payloads,
            )
            db.commit()
            return self._build_month_sheet(data.year, data.month, category, enabled, records)
        except Exception:
            db.rollback()
            logger.exception("保存废料销售价失败")
            raise

    def delete_month(
        self,
        db: Session,
        year: int,
        month: int,
        scrap_category: str,
    ) -> int:
        category = require_scrap_category(scrap_category)
        try:
            count = self.repository.delete_by_year_month_category(db, year, month, category)
            if count == 0:
                label = SCRAP_CATEGORY_LABELS[category]
                raise NotFoundException(f"{year}-{month:02d} {label}没有可删除的数据")
            db.commit()
            return count
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("删除废料销售价失败")
            raise

    def copy_month(
        self,
        db: Session,
        body: StampingScrapPriceCopyMonth,
        current_user: UserVO,
    ) -> StampingScrapPriceCopyMonthResponse:
        if body.source_year == body.target_year and body.source_month == body.target_month:
            raise BusinessException("源年月与目标年月不能相同")
        category = body.scrap_category
        enabled = self._enabled_locations(db)
        if not enabled:
            raise BusinessException("没有已启用基地，请到基地页启用")

        source_records = self.repository.list_by_year_month(
            db,
            body.source_year,
            body.source_month,
            scrap_category=category,
        )
        if not source_records:
            label = SCRAP_CATEGORY_LABELS[category]
            raise NotFoundException(
                f"源年月 {body.source_year}-{body.source_month:02d} {label}没有数据"
            )

        by_location = {r.location: r for r in source_records}
        missing = [name for name in enabled if name not in by_location]
        if missing:
            raise BusinessException(
                f"源月数据不完整，缺少: {', '.join(missing)}；请先补全源月再复制"
            )

        audit = audit_create(current_user)
        payloads: list[ScrapPriceWrite] = []
        for location in enabled:
            source = by_location[location]
            payloads.append(
                ScrapPriceWrite(
                    location=location,
                    scrap_category=category,
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
            records = self.repository.replace_year_month_category(
                db,
                body.target_year,
                body.target_month,
                category,
                payloads,
            )
            db.commit()
            return StampingScrapPriceCopyMonthResponse(
                source_year=body.source_year,
                source_month=body.source_month,
                target_year=body.target_year,
                target_month=body.target_month,
                scrap_category=category,
                created_count=len(records),
            )
        except Exception:
            db.rollback()
            logger.exception("复制废料销售价失败")
            raise
