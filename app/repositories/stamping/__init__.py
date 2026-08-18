"""冲压 Repositories 包。"""

from app.repositories.stamping.base import BaseRepository
from app.repositories.stamping.stamping_part_repository import StampingPartRepository
from app.repositories.stamping.stamping_process_repository import (
    StampingProcessRepository,
)
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)
from app.repositories.stamping.tonnage_price_repository import (
    StampingTonnagePriceRepository,
)

__all__ = [
    "BaseRepository",
    "StampingPartRepository",
    "StampingProcessRepository",
    "StampingTonnagePriceRepository",
    "StampingProcessFeeRepository",
]
