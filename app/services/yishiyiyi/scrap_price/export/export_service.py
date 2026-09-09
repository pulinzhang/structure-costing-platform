"""废料月度销售价格导出服务：查库 + 调导出器。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.location.location_service import LocationService
from app.services.yishiyiyi.scrap_price.export.excel_exporter import (
    StampingScrapPriceExporter,
)


class StampingScrapPriceExportService:
    """废料销售价宽表导出。"""

    def __init__(self) -> None:
        self.repository = StampingScrapPriceRepository()
        self._exporter = StampingScrapPriceExporter()

    def export(
        self,
        db: Session,
        *,
        year: int | None = None,
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        years = [year] if year is not None else self.repository.list_years_asc(db)
        records_by_year = {
            year_value: self.repository.list_by_year(db, year_value) for year_value in years
        }
        locations = LocationService().list_registered(db)
        return self._exporter.generate(
            years,
            records_by_year,
            locations=locations,
            year_filter=year,
            current_user=current_user,
        )
