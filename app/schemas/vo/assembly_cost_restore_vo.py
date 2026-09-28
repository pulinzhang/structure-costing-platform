"""总成核价成本还原报告 VO。"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.common.money import Q4
from app.common.timezone import datetime_to_iso
from app.services.costing.steel_price.spec_format import format_thickness


def _money_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    quantized = value.quantize(Q4, rounding=ROUND_HALF_UP)
    return f"{quantized:.4f}"


class RestoreIdentityCheckVO(BaseModel):
    code: str
    label: str
    recorded: Decimal
    summed: Decimal
    is_match: bool

    @field_serializer("recorded", "summed")
    def _ser_money(self, value: Decimal) -> str:
        return _money_str(value) or "0.0000"


class RestoreExceptionVO(BaseModel):
    kind: str
    message: str
    short_code: str = ""
    part_number: str | None = None


class RestoreProcessOpVO(BaseModel):
    process_seq: str | None = None
    process_code: str | None = None
    original_tonnage: int | None = None
    resolved_tonnage: int | None = None
    tonnage_source: str | None = None
    inherited_from_part_number: str | None = None
    inherited_from_process_seq: str | None = None
    cost_ratio: Decimal | None = None
    price_per_stroke: Decimal | None = None
    line_fee: Decimal
    basis_text: str | None = None

    @field_serializer("price_per_stroke", "line_fee", "cost_ratio")
    def _ser_money(self, value: Decimal | None) -> str | None:
        return _money_str(value)


class RestoreDieOpVO(BaseModel):
    process_seq: str
    process_code: str | None = None
    estimated_weight_t: Decimal | None = None
    alloc_ratio: Decimal | None = None
    die_sets: int | None = None
    unit_price: Decimal
    allocation_qty: Decimal | None = None
    price_kind: str | None = None
    line_die_fee: Decimal
    basis_text: str | None = None

    @field_serializer(
        "estimated_weight_t",
        "alloc_ratio",
        "unit_price",
        "allocation_qty",
        "line_die_fee",
    )
    def _ser_money(self, value: Decimal | None) -> str | None:
        return _money_str(value)


class RestoreSteelVO(BaseModel):
    steel_mill: str | None = None
    steel_ton_price: Decimal | None = None
    steel_price_id: int | None = None
    record_exists: bool = False
    missing_reason: str | None = None
    base_price: Decimal | None = None
    thickness_adjustment: Decimal | None = None
    width_adjustment: Decimal | None = None
    zinc_adjustment: Decimal | None = None
    processing_fee: Decimal | None = None
    other_adjustment: Decimal | None = None
    final_price_per_ton: Decimal | None = None
    base_excel_filename: str | None = None
    base_excel_row: int | None = None
    thickness_excel_filename: str | None = None
    thickness_excel_row: int | None = None

    @field_serializer(
        "steel_ton_price",
        "base_price",
        "thickness_adjustment",
        "width_adjustment",
        "zinc_adjustment",
        "processing_fee",
        "other_adjustment",
        "final_price_per_ton",
    )
    def _ser_money(self, value: Decimal | None) -> str | None:
        return _money_str(value)


class RestoreSupplierCostVO(BaseModel):
    stamping_supplier: str
    unit_cost: Decimal

    @field_serializer("unit_cost")
    def _ser_money(self, value: Decimal) -> str:
        return _money_str(value) or "0.0000"


class RestoreStampingVO(BaseModel):
    record_id: int | None = None
    record_missing: bool = False
    missing_reason: str | None = None
    stamping_supplier: str | None = None
    same_unit_cost_note: str | None = None
    conflict_rows: list[RestoreSupplierCostVO] = Field(default_factory=list)
    unit_cost: Decimal | None = None
    direct_cost: Decimal | None = None
    formula_version: str | None = None
    is_offal_nested: bool = False
    offal_source: str | None = None
    material_amount_sheet: Decimal | None = None
    loss_scrap_deduction: Decimal | None = None
    process_scrap_deduction: Decimal | None = None
    material_net_per_part: Decimal | None = None
    blank_weight_kg: Decimal | None = None
    finished_total_kg: Decimal | None = None
    scrap_weight_kg: Decimal | None = None
    density: Decimal | None = None
    material_loss_rate: Decimal | None = None
    scrap_recovery_rate: Decimal | None = None
    material: str | None = None
    sheet_length: Decimal | None = None
    sheet_width: Decimal | None = None
    thickness: Decimal | None = None
    parts_per_sheet: int | None = None
    swing_shear_fee_per_ton: Decimal | None = None
    steel: RestoreSteelVO | None = None
    scrap_price_id: int | None = None
    scrap_ton_price: Decimal | None = None
    scrap_record_exists: bool = False
    process_fee_id: int | None = None
    process_fee_amount: Decimal | None = None
    process_excel_filename: str | None = None
    process_ops: list[RestoreProcessOpVO] = Field(default_factory=list)
    die_fee_id: int | None = None
    die_fee_amount: Decimal | None = None
    die_system_fee: Decimal | None = None
    die_adjustment_amount: Decimal | None = None
    die_unit_price: Decimal | None = None
    die_allocation_qty: Decimal | None = None
    die_price_kind: str | None = None
    die_excel_filename: str | None = None
    die_ops: list[RestoreDieOpVO] = Field(default_factory=list)
    gauge_fee_id: int | None = None
    gauge_fee_amount: Decimal | None = None
    gauge_record_exists: bool = False
    finished_finance_fee: Decimal | None = None
    finished_management_fee: Decimal | None = None
    finished_warehouse_packaging_fee: Decimal | None = None
    finished_pretax_profit_fee: Decimal | None = None
    excel_filename: str | None = None
    excel_row: int | None = None

    @field_serializer("thickness")
    def _ser_thickness(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        text = format_thickness(value)
        return text or None

    @field_serializer(
        "unit_cost",
        "direct_cost",
        "material_amount_sheet",
        "loss_scrap_deduction",
        "process_scrap_deduction",
        "material_net_per_part",
        "swing_shear_fee_per_ton",
        "scrap_ton_price",
        "process_fee_amount",
        "die_fee_amount",
        "die_system_fee",
        "die_adjustment_amount",
        "die_unit_price",
        "die_allocation_qty",
        "gauge_fee_amount",
        "finished_finance_fee",
        "finished_management_fee",
        "finished_warehouse_packaging_fee",
        "finished_pretax_profit_fee",
    )
    def _ser_money(self, value: Decimal | None) -> str | None:
        return _money_str(value)


class RestoreAnnualVO(BaseModel):
    record_missing: bool = False
    missing_reason: str | None = None
    unit_price: Decimal | None = None
    supplier_name: str | None = None
    supply_type: str | None = None

    @field_serializer("unit_price")
    def _ser_money(self, value: Decimal | None) -> str | None:
        return _money_str(value)


class RestoreMaterialNodeVO(BaseModel):
    sort_no: int
    indent_level: int
    node_level: int
    bom_node_id: int | None = None
    part_number: str
    part_name: str | None = None
    short_code: str
    seq_label: str = ""
    node_role: str | None = None
    supply_type: str | None = None
    cost_source: str
    cost_source_label: str
    unit_price: Decimal
    effective_qty: Decimal
    line_amount: Decimal
    stamping: RestoreStampingVO | None = None
    annual: RestoreAnnualVO | None = None

    @field_serializer("unit_price", "line_amount")
    def _ser_money(self, value: Decimal) -> str:
        return _money_str(value) or "0.0000"

    @field_serializer("effective_qty")
    def _ser_qty(self, value: Decimal) -> str:
        return f"{value.normalize()}"


class RestoreWeldingLineVO(BaseModel):
    line_no: int
    process_token: str | None = None
    standard_process_name: str | None = None
    process_qty: Decimal
    unit_price: Decimal | None = None
    line_fee: Decimal | None = None
    match_status: str
    source_breakdown_line_id: int | None = None

    @field_serializer("process_qty")
    def _ser_qty(self, value: Decimal) -> str:
        return f"{value.normalize()}"

    @field_serializer("unit_price", "line_fee")
    def _ser_money(self, value: Decimal | None) -> str | None:
        return _money_str(value)


class RestoreWeldingVO(BaseModel):
    has_record: bool
    message: str | None = None
    welding_fee_id: int | None = None
    weld_info_raw: str | None = None
    total_welding_fee: Decimal | None = None
    other_fee: Decimal | None = None
    final_welding_fee: Decimal | None = None
    calc_status: str | None = None
    fee_level: int | None = None
    card_level: int | None = None
    level_mismatch: bool = False
    items: list[RestoreWeldingLineVO] = Field(default_factory=list)

    @field_serializer("total_welding_fee", "other_fee", "final_welding_fee")
    def _ser_money(self, value: Decimal | None) -> str | None:
        return _money_str(value)


class RestoreIndirectLineVO(BaseModel):
    code: str
    label: str
    kind: str
    amount: Decimal
    rate: Decimal | None = None
    base_amount: Decimal | None = None
    match_key: str | None = None
    note: str | None = None

    @field_serializer("amount", "base_amount")
    def _ser_money(self, value: Decimal | None) -> str | None:
        return _money_str(value)

    @field_serializer("rate")
    def _ser_rate(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return f"{value.quantize(Decimal('0.000001'))}"


class RestoreDocumentRefVO(BaseModel):
    file_category: str
    file_category_label: str
    filename: str
    excel_row: int | None = None
    cited_short_codes: list[str] = Field(default_factory=list)


class AssemblyCostRestoreVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    view: str
    highlight_label: str
    highlight_amount: Decimal
    id: int
    year: int
    month: int
    location: str
    vehicle_model: str
    bom_version: str
    part_number: str
    part_name: str | None = None
    short_code: str
    calc_status: str
    audit_status: str
    calculated_at: datetime | None = None
    stamping_amount: Decimal
    purchased_amount: Decimal
    bundle_amount: Decimal
    welding_amount: Decimal
    total_amount: Decimal
    should_cost: Decimal
    indirect_amount: Decimal
    grand_total: Decimal
    identity_checks: list[RestoreIdentityCheckVO]
    exceptions: list[RestoreExceptionVO]
    material_nodes: list[RestoreMaterialNodeVO]
    welding: RestoreWeldingVO
    indirects: list[RestoreIndirectLineVO]
    documents: list[RestoreDocumentRefVO]
    company_name: str = ""
    calculated_by: str = ""
    is_purchased_assembly: bool = False

    @field_serializer("calculated_at")
    def _ser_dt(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    @field_serializer(
        "highlight_amount",
        "stamping_amount",
        "purchased_amount",
        "bundle_amount",
        "welding_amount",
        "total_amount",
        "should_cost",
        "indirect_amount",
        "grand_total",
    )
    def _ser_money(self, value: Decimal) -> str:
        return _money_str(value) or "0.0000"
