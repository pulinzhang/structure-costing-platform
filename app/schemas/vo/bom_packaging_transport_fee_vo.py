"""
BOM 包装运输费 VO
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer

from app.common.money import Q4, format_money
from app.common.timezone import datetime_to_iso
from app.schemas.common.batch_result import BatchAuditCountsVO, BatchDeleteCountsVO


def _money_str(value: Any) -> str:
    return format_money(value if value is not None else Decimal("0"), Q4, 4)


def _optional_money_str(value: Any) -> str | None:
    if value is None:
        return None
    return format_money(value, Q4, 4)


class BomPackagingTransportFeeResponse(BaseModel):
    """包装运输费响应 VO"""

    id: int
    location: str
    year: int
    vehicle_model: str
    part_number: str
    part_name: str | None = None
    packaging_type: str | None = None
    pieces_per_pack: int | None = None
    fixture_length_mm: int | None = None
    fixture_width_mm: int | None = None
    fixture_height_mm: int | None = None
    oem_stock_qty: int | None = None
    transit_qty: int | None = None
    company_stock_qty: int | None = None
    total_fixture_qty: int | None = None
    fixture_unit_price: Decimal | None = None
    fixture_invest_amount: Decimal | None = None
    unit_packaging_fee: Decimal
    round_trip_transport_price: Decimal | None = None
    unit_transport_fee: Decimal
    fixture_maint_fee: Decimal
    other_fee: Decimal
    packaging_transport_total: Decimal
    remark: str | None = None
    excel_filename: str | None = None
    sheet_name: str | None = None
    excel_row: int | None = None
    audit_status: str = "pending"
    audited_by: str | None = None
    audited_at: datetime | None = None
    audit_remark: str | None = None
    reverse_audited_by: str | None = None
    reverse_audited_at: datetime | None = None
    reverse_audit_remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer(
        "unit_packaging_fee",
        "unit_transport_fee",
        "fixture_maint_fee",
        "other_fee",
        "packaging_transport_total",
    )
    def serialize_required_money(self, value: Decimal) -> str:
        return _money_str(value)

    @field_serializer(
        "fixture_unit_price",
        "fixture_invest_amount",
        "round_trip_transport_price",
    )
    def serialize_optional_money(self, value: Decimal | None) -> str | None:
        return _optional_money_str(value)

    @field_serializer("created_at", "updated_at", "audited_at", "reverse_audited_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = ConfigDict(from_attributes=True)


class BomPackagingTransportFeeImportResultVO(BaseModel):
    """Excel 导入结果"""

    location: str
    year: int
    vehicle_model: str
    created_count: int
    updated_count: int
    total_count: int
    skipped_count: int = 0
    skipped_approved_count: int = 0
    warnings: list[str] = []
    message: str = ""
    source_filename: str | None = None


class BomPackagingTransportFeeBatchDeleteResultVO(BatchDeleteCountsVO):
    """批量删除结果"""

    location: str
    year: int
    vehicle_model: str
    message: str = ""


class BomPackagingTransportFeeBatchAuditResultVO(BatchAuditCountsVO):
    """批量审核 / 反审核结果"""

    location: str
    year: int
    vehicle_model: str
