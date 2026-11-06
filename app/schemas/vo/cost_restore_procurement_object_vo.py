"""成本还原 — 采购对象查询行。金额在 JSON 里是固定小数位字符串。"""

from pydantic import BaseModel, Field


class CostRestoreVehicleChoiceVO(BaseModel):
    location: str
    vehicle_model: str


class CostRestoreDefaultsVO(BaseModel):
    location: str | None = None
    year: int | None = None
    month: int | None = None
    vehicle_model: str | None = None
    locations: list[str] = Field(default_factory=list)
    vehicle_models: list[CostRestoreVehicleChoiceVO] = Field(default_factory=list)
    suppliers: list[str] = Field(default_factory=list)


class CostRestoreScopeVO(BaseModel):
    location: str
    year: int
    month: int
    vehicle_model: str | None = None
    scope_label: str
    qa_passed: bool
    qa_note: str | None = None


class CostRestoreLineVO(BaseModel):
    object_id: int
    supplier_name: str | None = None
    vehicle_model: str | None = None
    object_kind: str | None = None
    internal_number: str | None = None
    object_part_number: str | None = None
    object_part_name: str | None = None
    vehicle_qty: str | None = None
    settlement_price: str | None = None
    row_type: str
    leaf_part_number: str | None = None
    priced_part_number: str | None = None
    sheet_length: str | None = None
    sheet_width: str | None = None
    thickness: str | None = None
    parts_per_sheet: int | None = None
    blank_weight_kg: str | None = None
    material: str | None = None
    finished_weight_kg: str | None = None
    utilization_pct: str | None = None
    scrap_weight_kg: str | None = None
    scrap_price_per_kg: str | None = None
    swing_shear_fee_per_ton: str | None = None
    steel_price_per_kg: str | None = None
    material_amount_sheet: str | None = None
    loss_scrap_deduction: str | None = None
    process_scrap_deduction: str | None = None
    material_net: str | None = None
    automation: str | None = None
    process_code: str | None = None
    tonnage: int | None = None
    stroke_fee: str | None = None
    die_length: str | None = None
    die_width: str | None = None
    die_height: str | None = None
    hollow_factor: str | None = None
    die_sets: int | None = None
    die_weight_t: str | None = None
    material_cost: str | None = None
    process_cost: str | None = None
    material_plus_process: str | None = None
    die_fee: str | None = None
    gauge_fee: str | None = None
    finance_fee: str | None = None
    management_fee: str | None = None
    warehouse_fee: str | None = None
    profit_fee: str | None = None
    direct_cost: str | None = None
    unit_cost: str | None = None
    line_amount: str | None = None
    outsourced_amount: str | None = None
    weld_name: str | None = None
    weld_qty: str | None = None
    weld_unit_price: str | None = None
    weld_amount: str | None = None
    ecoat_amount: str | None = None
    part_cost_id: int | None = None
    process_fee_id: int | None = None
    die_fee_id: int | None = None
    gauge_fee_id: int | None = None
    steel_price_id: int | None = None
    scrap_price_id: int | None = None
    welding_fee_id: int | None = None
    source_filename: str | None = None
    source_row: int | None = None
    calc_status: str | None = None
    remark: str | None = None
