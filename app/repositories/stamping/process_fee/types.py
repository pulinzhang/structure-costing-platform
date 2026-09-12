"""冲压加工费列表筛选形状。"""

from decimal import Decimal
from typing import TypedDict

from sqlalchemy import or_
from sqlalchemy.sql.elements import ColumnElement

from app.models.stamping import StampingProcessFee


class ProcessFeeFilterSummary(TypedDict):
    """列表筛选汇总：总金额 / 件均 / 待补价 / 待审 / 已审 / 版本标签。"""

    total_count: int
    total_fee: Decimal
    avg_fee: Decimal | None
    zero_count: int
    pending_count: int
    approved_count: int
    version_label: str


class ProcessFeeListFilters(TypedDict):
    """冲压加工费列表筛选体。"""

    year: int | None
    location: str | None
    stamping_supplier: str | None
    vehicle_model: str | None
    version: str | None
    part_number: str | None
    audit_status: str | None
    only_zero: bool
    summary: ProcessFeeFilterSummary


def needs_price_fix_clause() -> ColumnElement[bool]:
    """确认单价为空或为 0：算费失败 / 零价且尚未补价。"""
    return or_(
        StampingProcessFee.final_processing_fee.is_(None),
        StampingProcessFee.final_processing_fee == 0,
    )
