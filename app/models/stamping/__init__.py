"""冲压切片 ORM。"""

from app.models.stamping.part import StampingPart, StampingProcess
from app.models.stamping.process_fee import StampingProcessFee
from app.models.stamping.process_fee_calc_log import StampingProcessFeeCalcLog
from app.models.stamping.process_fee_item import StampingProcessFeeItem
from app.models.stamping.tonnage_price import StampingTonnagePrice

__all__ = [
    "StampingPart",
    "StampingProcess",
    "StampingProcessFee",
    "StampingProcessFeeCalcLog",
    "StampingProcessFeeItem",
    "StampingTonnagePrice",
]
