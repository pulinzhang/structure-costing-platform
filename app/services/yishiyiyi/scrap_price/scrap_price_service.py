"""
冲压废料月度销售价格 Service（门面）

CRUD / 导出见各子包；本模块仅委托并保持对外 API。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.schemas.dto.stamping_scrap_price_dto import (
    StampingScrapPriceCopyMonth,
    StampingScrapPriceMonthSaveDTO,
)
from app.schemas.vo.stamping_scrap_price_vo import (
    StampingScrapPriceCopyMonthResponse,
    StampingScrapPriceFilterOptionsVO,
    StampingScrapPriceMonthSheetVO,
    StampingScrapPriceMonthSummaryVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.yishiyiyi.scrap_price.crud.scrap_price_crud import (
    StampingScrapPriceCrudService,
)

__all__ = ["StampingScrapPriceService"]


class StampingScrapPriceService:
    """废料销售价格业务逻辑（按月）：委托 CRUD。"""

    def __init__(self) -> None:
        self._crud = StampingScrapPriceCrudService()
        self.repository = self._crud.repository

    def get_month_sheet(
        self,
        db: Session,
        year: int,
        month: int,
        scrap_category: str,
    ) -> StampingScrapPriceMonthSheetVO:
        return self._crud.get_month_sheet(db, year, month, scrap_category)

    def list_month_summaries(
        self,
        db: Session,
        year: int | None = None,
        *,
        scrap_category: str,
    ) -> list[StampingScrapPriceMonthSummaryVO]:
        return self._crud.list_month_summaries(db, year=year, scrap_category=scrap_category)

    def get_filter_options(self, db: Session) -> StampingScrapPriceFilterOptionsVO:
        return self._crud.get_filter_options(db)

    def save_month(
        self,
        db: Session,
        data: StampingScrapPriceMonthSaveDTO,
        current_user: UserVO,
    ) -> StampingScrapPriceMonthSheetVO:
        return self._crud.save_month(db, data, current_user)

    def delete_month(
        self,
        db: Session,
        year: int,
        month: int,
        scrap_category: str,
    ) -> int:
        return self._crud.delete_month(db, year, month, scrap_category)

    def copy_month(
        self,
        db: Session,
        body: StampingScrapPriceCopyMonth,
        current_user: UserVO,
    ) -> StampingScrapPriceCopyMonthResponse:
        return self._crud.copy_month(db, body, current_user)
