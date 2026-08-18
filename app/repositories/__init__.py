# Repositories Package

from app.repositories.stamping import StampingPartRepository, StampingProcessRepository
from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.repositories.yishiyiyi.scrap_price import StampingScrapPriceRepository

__all__ = [
    "StampingPartRepository",
    "StampingProcessRepository",
    "StampingTonnagePriceRepository",
    "StampingScrapPriceRepository",
]
