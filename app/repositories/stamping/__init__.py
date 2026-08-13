# Stamping Repositories Package

from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.repositories.stamping.scrap_price_repository import StampingScrapPriceRepository

__all__ = [
    "StampingPartRepository",
    "StampingProcessRepository",
    "StampingTonnagePriceRepository",
    "StampingScrapPriceRepository",
]
