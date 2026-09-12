"""包装运输费解析结果类型。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PackagingTransportFeeParsedRow:
    """解析后的一行"""

    row_number: int
    part_number: str
    part_name: str | None
    packaging_type: str | None
    pieces_per_pack: int | None
    fixture_length_mm: int | None
    fixture_width_mm: int | None
    fixture_height_mm: int | None
    oem_stock_qty: int | None
    transit_qty: int | None
    company_stock_qty: int | None
    total_fixture_qty: int | None
    fixture_unit_price: Decimal | None
    fixture_invest_amount: Decimal | None
    unit_packaging_fee: Decimal
    round_trip_transport_price: Decimal | None
    unit_transport_fee: Decimal
    fixture_maint_fee: Decimal
    other_fee: Decimal
    packaging_transport_total: Decimal
    remark: str | None


@dataclass(frozen=True)
class PackagingTransportFeeParseResult:
    rows: list[PackagingTransportFeeParsedRow]
    errors: list[str]
    sheet_name: str | None = None
