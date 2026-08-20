"""成品月核价 VO。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.common.money import Q4


def _money_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    quantized = value.quantize(Q4, rounding=ROUND_HALF_UP)
    return f"{quantized:.4f}"


class L0AssemblyCostItemVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    level_label: str
    bom_node_id: int | None = None
    part_number: str
    part_name: str | None = None
    node_role: str | None = None
    supply_type: str | None = None
    cost_source: str
    match_hint: str | None = None
    unit_price: Decimal
    effective_qty: Decimal
    line_amount: Decimal
    sort_no: int

    @field_serializer("unit_price", "line_amount")
    def _ser_money(self, value: Decimal) -> str:
        return _money_str(value) or "0.0000"

    @field_serializer("effective_qty")
    def _ser_qty(self, value: Decimal) -> str:
        return f"{value.normalize()}"


class L0AssemblyCostIndirectVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    label: str
    amount: Decimal
    rate: Decimal | None = None
    base_amount: Decimal | None = None
    sort_no: int

    @field_serializer("amount", "base_amount")
    def _ser_money(self, value: Decimal | None) -> str | None:
        return _money_str(value)

    @field_serializer("rate")
    def _ser_rate(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return f"{value.quantize(Decimal('0.000001'))}"


class L0AssemblyCostVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    year: int
    month: int
    location: str
    vehicle_model: str
    bom_version: str
    part_number: str
    part_name: str | None = None
    supply_qty: Decimal
    sketch_url: str | None = None
    stamping_amount: Decimal
    purchased_amount: Decimal
    bundle_amount: Decimal
    material_amount: Decimal
    welding_amount: Decimal
    welding_other_fee: Decimal
    total_amount: Decimal
    unit_transport_fee: Decimal
    warehouse_bundling_fee: Decimal
    finished_finance_fee: Decimal
    finished_management_fee: Decimal
    finished_scrap_fee: Decimal
    finished_pretax_profit_fee: Decimal
    gauge_alloc_fee: Decimal
    fixture_alloc_fee: Decimal
    allocation_fee_total: Decimal
    indirect_amount: Decimal
    grand_total: Decimal
    finance_rate: Decimal
    management_rate: Decimal
    scrap_rate: Decimal
    pretax_profit_rate: Decimal
    welding_fee_id: int | None = None
    welding_summary: str | None = None
    calc_status: str
    missing_leaf_count: int
    calc_message: str | None = None
    formula_version: str | None = None
    calculated_at: datetime | None = None
    audit_status: str
    audited_by: str | None = None
    audited_at: datetime | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    items: list[L0AssemblyCostItemVO] = Field(default_factory=list)
    indirects: list[L0AssemblyCostIndirectVO] = Field(default_factory=list)

    @field_serializer(
        "stamping_amount",
        "purchased_amount",
        "bundle_amount",
        "material_amount",
        "welding_amount",
        "welding_other_fee",
        "total_amount",
        "unit_transport_fee",
        "warehouse_bundling_fee",
        "finished_finance_fee",
        "finished_management_fee",
        "finished_scrap_fee",
        "finished_pretax_profit_fee",
        "gauge_alloc_fee",
        "fixture_alloc_fee",
        "allocation_fee_total",
        "indirect_amount",
        "grand_total",
        "supply_qty",
    )
    def _ser_money(self, value: Decimal) -> str:
        return _money_str(value) or "0.0000"

    @field_serializer(
        "finance_rate", "management_rate", "scrap_rate", "pretax_profit_rate"
    )
    def _ser_rate(self, value: Decimal) -> str:
        return f"{value.quantize(Decimal('0.000001'))}"

    @field_serializer("calculated_at", "audited_at", "created_at", "updated_at")
    def _ser_dt(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class L0AssemblyCostListSummaryVO(BaseModel):
    total_count: int
    ok_count: int
    partial_count: int
    pending_count: int
    approved_count: int
    grand_total_sum: Decimal
    total_amount_sum: Decimal

    @field_serializer("grand_total_sum", "total_amount_sum")
    def _ser_money(self, value: Decimal) -> str:
        return _money_str(value) or "0.0000"


class L0AssemblyCostCalcReadyVO(BaseModel):
    l0_count: int
    stamping_price_count: int
    annual_price_count: int
    welding_fee_count: int
    packaging_fee_count: int
    bom_version: str
    ready: bool
    message: str | None = None


class L0AssemblyCostCalcResultVO(BaseModel):
    status: str
    created_count: int
    updated_count: int
    skipped_approved_count: int
    ok_count: int
    partial_count: int
    failed_count: int
    message: str | None = None


class L0AssemblyCostCalcLogVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    year: int
    month: int
    location: str
    vehicle_model: str
    bom_version: str
    calc_batch_id: str
    status: str
    message: str | None = None
    l0_total: int
    ok_count: int
    partial_count: int
    failed_count: int
    skipped_approved_count: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    operator_name: str | None = None

    @field_serializer("started_at", "finished_at")
    def _ser_dt(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class L0AssemblyCostBatchResultVO(BaseModel):
    affected_count: int
    skipped_count: int = 0
    message: str | None = None
