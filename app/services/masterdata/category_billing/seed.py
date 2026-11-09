"""计费对照空库种子。已有任意行则不覆盖。

现网总成核价每张卡都计这五项：运输、仓储+包装、财务费、管理费、税前利润。
报废、检具、器具不在费用档案里，不进种子。
"""

from app.services.masterdata.assembly_category.seed import ASSEMBLY_CATEGORY_SEEDS
from app.services.masterdata.fee_archive.seed import FEE_ARCHIVE_SEEDS

BILLING_SEED_PAIRS: tuple[tuple[str, str], ...] = tuple(
    (category.code, fee.code) for category in ASSEMBLY_CATEGORY_SEEDS for fee in FEE_ARCHIVE_SEEDS
)
