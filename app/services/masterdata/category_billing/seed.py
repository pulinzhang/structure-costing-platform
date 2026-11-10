"""计费对照空库种子。已有任意行则不覆盖。

四个分类都勾上费用档案里的种子费用。库里已经有对照时，只给新补上的费用代码勾选。
"""

from app.services.masterdata.assembly_category.seed import ASSEMBLY_CATEGORY_SEEDS
from app.services.masterdata.fee_archive.seed import FEE_ARCHIVE_SEEDS

BILLING_SEED_PAIRS: tuple[tuple[str, str], ...] = tuple(
    (category.code, fee.code) for category in ASSEMBLY_CATEGORY_SEEDS for fee in FEE_ARCHIVE_SEEDS
)
