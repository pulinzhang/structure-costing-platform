"""冲压零件价格核算 VO。"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.common.money import Q2, Q3, Q4, Q6, format_money, optional_format_money
from app.common.timezone import datetime_to_iso
from app.schemas.common.batch_result import BatchAuditCountsVO, BatchDeleteCountsVO
from app.schemas.vo.timing import DurationSecondsMixin


class StampingPartCostVO(BaseModel):
    """零件价格核算结果行。"""

    id: int
    year: int
    month: int
    location: str
    stamping_supplier: str
    vehicle_model: str
    version: str
    source_part_id: int
    seq_no: int | None = None
    part_number: str
    part_name: str | None = None
    material: str | None = None
    thickness: str | None = None
    part_weight: Decimal | None = None
    sheet_length: str | None = None
    sheet_width: str | None = None
    parts_per_sheet: int | None = None
    sheet_type: str | None = None
    is_offal_nested: bool = False
    offal_source: str | None = None
    has_swing_shear: bool = False
    swing_shear_fee_per_ton: Decimal = Decimal("0")
    die_type: str | None = None
    process_method: str | None = None
    automation: str | None = None
    part_remark: str | None = None
    sketch_url: str | None = None
    excel_filename: str | None = None
    excel_sheet_name: str | None = None
    excel_row: int | None = None
    excel_part_col: int | None = None

    density: Decimal | None = None
    material_loss_rate: Decimal | None = None
    scrap_recovery_rate: Decimal | None = None
    blank_weight_kg: Decimal | None = None
    finished_total_kg: Decimal | None = None
    scrap_weight_kg: Decimal | None = None
    material_utilization_pct: Decimal | None = None

    steel_price_id: int | None = None
    steel_mill: str | None = None
    steel_ton_price: str | None = None
    scrap_price_id: int | None = None
    scrap_ton_price: Decimal | None = None
    process_fee_id: int | None = None
    process_fee_amount: Decimal | None = None
    die_fee_id: int | None = None
    die_fee_amount: Decimal | None = None
    gauge_fee_id: int | None = None
    gauge_fee_amount: Decimal | None = None

    material_amount_sheet: Decimal | None = None
    loss_scrap_deduction: Decimal | None = None
    process_scrap_deduction: Decimal | None = None
    scrap_amount_sheet: Decimal | None = None
    material_net_per_part: Decimal | None = None
    direct_cost: Decimal | None = None
    finished_finance_fee: Decimal | None = None
    finished_management_fee: Decimal | None = None
    finished_warehouse_packaging_fee: Decimal | None = None
    finished_pretax_profit_fee: Decimal | None = None
    unit_cost: Decimal | None = None

    calc_batch_id: str | None = None
    calc_status: str = "success"
    calc_fail_reason: str | None = None
    formula_version: str | None = None
    calculated_at: datetime | None = None
    remark: str | None = None

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

    @field_validator(
        "thickness",
        "sheet_length",
        "sheet_width",
        "steel_ton_price",
        mode="before",
    )
    @classmethod
    def _display_string(cls, value: object) -> str | None:
        """ORM Decimal 不直接当展示串；由 Service 填入 0.70/1.00 这类文本。"""
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return value
        return None

    @field_serializer("part_weight", "density", "material_utilization_pct")
    def serialize_q4(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("material_loss_rate", "scrap_recovery_rate")
    def serialize_rate(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q6, 6)

    @field_serializer("blank_weight_kg", "finished_total_kg", "scrap_weight_kg")
    def serialize_weight(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q6, 6)

    @field_serializer("scrap_ton_price")
    def serialize_ton_price(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("swing_shear_fee_per_ton")
    def serialize_swing_shear_fee(self, value: Decimal) -> str:
        return format_money(value, Q2, 2)

    @field_serializer("process_fee_amount")
    def serialize_process_fee(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q3, 3)

    @field_serializer(
        "material_amount_sheet",
        "loss_scrap_deduction",
        "process_scrap_deduction",
        "scrap_amount_sheet",
        "material_net_per_part",
        "die_fee_amount",
        "gauge_fee_amount",
        "direct_cost",
        "finished_finance_fee",
        "finished_management_fee",
        "finished_warehouse_packaging_fee",
        "finished_pretax_profit_fee",
        "unit_cost",
    )
    def serialize_amount(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q6, 6)

    @field_serializer(
        "created_at",
        "updated_at",
        "audited_at",
        "reverse_audited_at",
        "calculated_at",
    )
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = ConfigDict(from_attributes=True)


class StampingPartCostFailedItemVO(BaseModel):
    """计算失败零件摘要。"""

    part_number: str
    part_name: str | None = None
    reason: str


class StampingPartCostCalcResultVO(BaseModel):
    """异步计算完成后的汇总。"""

    year: int
    month: int
    location: str
    stamping_supplier: str
    vehicle_model: str | None = None
    version: str | None = None
    calc_batch_id: str | None = None
    log_id: int | None = None
    status: str = "success"
    total_parts: int
    success_count: int
    failed_count: int
    skipped_approved_count: int = 0
    failed_items: list[StampingPartCostFailedItemVO] = Field(default_factory=list)
    detail_text: str = ""
    started_at: str | None = None
    finished_at: str | None = None


class StampingPartCostCalcLogVO(DurationSecondsMixin):
    """计算历史行。"""

    id: int
    calc_batch_id: str
    year: int
    month: int
    location: str
    stamping_supplier: str
    vehicle_model: str | None = None
    version: str | None = None
    status: str
    total_parts: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_approved_count: int = 0
    detail_text: str = ""
    operator_id: int | None = None
    operator_name: str | None = None
    created_by: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None

    @field_serializer("started_at", "finished_at", "created_at")
    def serialize_log_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


class StampingPartCostCalcReadyVO(BaseModel):
    """计算前数据就绪统计。"""

    year: int
    month: int | None = None
    location: str | None = None
    stamping_supplier: str | None = None
    vehicle_model: str | None = None
    version: str | None = None
    part_count: int = 0
    steel_price_count: int = 0
    scrap_price_count: int = 0
    process_fee_count: int = 0
    die_fee_count: int = 0
    gauge_fee_count: int = 0
    can_calculate: bool = False
    message: str | None = None


class StampingPartCostBatchDeleteResultVO(BatchDeleteCountsVO):
    year: int
    month: int
    location: str
    vehicle_model: str
    version: str | None = None
    stamping_supplier: str | None = None


class StampingPartCostBatchAuditResultVO(BatchAuditCountsVO):
    year: int
    month: int
    location: str
    vehicle_model: str
    version: str | None = None
    stamping_supplier: str | None = None
