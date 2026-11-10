"""费用档案空库种子。已有任意行则不覆盖。"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FeeArchiveSeed:
    sort_order: int
    code: str
    name: str
    charge_basis: str
    charge_rate: Decimal


FEE_ARCHIVE_SEEDS: tuple[FeeArchiveSeed, ...] = (
    FeeArchiveSeed(1, "warehouse_packaging", "仓储+包装", "amount", Decimal("0.01")),
    FeeArchiveSeed(2, "transport", "运输", "amount", Decimal("0.02")),
    FeeArchiveSeed(3, "management", "管理费", "rate", Decimal("0.02")),
    FeeArchiveSeed(4, "financial", "财务费", "rate", Decimal("0.02")),
    FeeArchiveSeed(5, "scrap", "报废费用", "rate", Decimal("0.003")),
    FeeArchiveSeed(6, "pretax_profit", "税前利润", "rate", Decimal("0.02")),
)
