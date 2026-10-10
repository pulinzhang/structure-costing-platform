"""钢材价格：最终价公式、已审保护。"""

from __future__ import annotations

from decimal import Decimal

from app.common.audit import AUDIT_APPROVED
from app.exceptions.base import BusinessException
from app.models.costing import SteelPrice

FORMULA_VERSION = "v1"


def compute_final_price(
    *,
    base_price: Decimal,
    thickness_adjustment: Decimal,
    width_adjustment: Decimal,
    zinc_adjustment: Decimal,
    processing_fee: Decimal,
    other_adjustment: Decimal,
) -> Decimal:
    return (
        base_price
        + thickness_adjustment
        + width_adjustment
        + zinc_adjustment
        + processing_fee
        + other_adjustment
    )


def ensure_not_approved(record: SteelPrice) -> None:
    if record.audit_status == AUDIT_APPROVED:
        raise BusinessException("记录已审核通过，请先反审核后再修改/删除/重算")
