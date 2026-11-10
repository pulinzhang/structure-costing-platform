"""核算读取的成品费率。数字在费用档案上，勾选在计费管理。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

STAMPING_CATEGORY_CODE = "stamping"
ASSEMBLY_CATEGORY_CODE = "assembly"


@dataclass(frozen=True, slots=True)
class FinishedFeeRates:
    finance_rate: Decimal
    management_rate: Decimal
    warehouse_packaging_rate: Decimal
    scrap_rate: Decimal
    pretax_profit_rate: Decimal

    @classmethod
    def zeros(cls) -> FinishedFeeRates:
        """五项都是 0。设置关闭成品费率时用。"""
        zero = Decimal("0")
        return cls(
            finance_rate=zero,
            management_rate=zero,
            warehouse_packaging_rate=zero,
            scrap_rate=zero,
            pretax_profit_rate=zero,
        )
