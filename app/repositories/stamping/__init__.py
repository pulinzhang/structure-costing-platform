# Stamping Repositories Package

from app.repositories.stamping.stamping_repository import (
    StampingPartRepository,
    StampingProcessRepository,
)
from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository

__all__ = [
    "StampingPartRepository",
    "StampingProcessRepository",
    "StampingTonnagePriceRepository",
]
