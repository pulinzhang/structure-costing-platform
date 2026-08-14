"""
冲压加工费 VO - 响应数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Union

from pydantic import BaseModel, Field, field_serializer


def decimal_to_float(value: Union[Decimal, float, None]) -> float | None:
    return float(value) if isinstance(value, Decimal) else value


class StampingProcessFeeItemVO(BaseModel):
    """加工费工序分项（单价计算依据）"""

    id: int | None = None
    source_process_id: int | None = None
    process_seq: str | None = None
    process_order: int | None = None
    process_code: str | None = None
    original_tonnage: int | None = None
    resolved_tonnage: int | None = None
    tonnage_source: str = "self"
    inherited_from_part_id: int | None = None
    inherited_from_part_number: str | None = None
    inherited_from_process_seq: str | None = None
    inherited_from_process_code: str | None = None
    cost_ratio: float | None = None
    tonnage_price_id: int | None = None
    price_per_stroke: float | None = None
    line_fee: float | None = None
    basis_text: str | None = None
    remark: str | None = None

    @field_serializer("cost_ratio", "price_per_stroke", "line_fee")
    def serialize_item_decimal(
        self, value: Union[Decimal, float, None]
    ) -> float | None:
        return decimal_to_float(value)

    model_config = {"from_attributes": True}


class StampingProcessFeeVO(BaseModel):
    """冲压加工费结果行"""

    id: int
    year: int
    location: str
    stamping_supplier: str
    vehicle_model: str
    version: str
    source_part_id: int | None = None
    seq_no: int | None = None
    part_number: str
    part_name: str | None = None
    material: str | None = None
    thickness: float | None = None
    part_weight: float | None = None
    sheet_length: float | None = None
    sheet_width: float | None = None
    parts_per_sheet: int | None = None
    sheet_type: str | None = None
    die_type: str | None = None
    process_method: str | None = None
    automation: str | None = None
    part_remark: str | None = None
    sketch_url: str | None = None
    excel_filename: str | None = None
    processing_fee: float | None = None
    process_count: int
    manual_unit_price: float | None = None
    final_processing_fee: float | None = None
    calc_fail_reason: str | None = None
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
    process_items: list[StampingProcessFeeItemVO] = Field(default_factory=list)

    @field_serializer(
        "processing_fee",
        "manual_unit_price",
        "final_processing_fee",
        "thickness",
        "part_weight",
        "sheet_length",
        "sheet_width",
    )
    def serialize_fee(self, value: Union[Decimal, float, None]) -> float | None:
        return decimal_to_float(value)

    @field_serializer(
        "created_at",
        "updated_at",
        "audited_at",
        "reverse_audited_at",
    )
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    model_config = {"from_attributes": True}


class StampingProcessFeeFailedItemVO(BaseModel):
    """计算失败零件/工序摘要"""

    part_number: str
    part_name: str | None = None
    process_seq: str | None = None
    process_code: str | None = None
    process_method: str | None = None
    reason: str


class StampingProcessFeeCalcResultVO(BaseModel):
    """冲压加工费计算汇总（异步任务完成后的 result）"""

    year: int
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
    zero_fee_count: int = 0
    skipped_approved_count: int = 0
    failed_items: list[StampingProcessFeeFailedItemVO] = []
    zero_fee_items: list[StampingProcessFeeFailedItemVO] = []
    detail_text: str = ""
    started_at: str | None = None
    finished_at: str | None = None


class StampingProcessFeeCalcLogVO(BaseModel):
    """计算历史行"""

    model_config = {"from_attributes": True}

    id: int
    calc_batch_id: str
    year: int
    location: str
    stamping_supplier: str
    vehicle_model: str | None = None
    version: str | None = None
    status: str
    total_parts: int = 0
    success_count: int = 0
    failed_count: int = 0
    zero_fee_count: int = 0
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
        return value.isoformat() if value else None


class StampingProcessFeeCalcReadyVO(BaseModel):
    """计算前数据就绪统计"""

    year: int
    location: str | None = None
    stamping_supplier: str | None = None
    vehicle_model: str | None = None
    version: str | None = None
    part_count: int = 0
    tonnage_rate_count: int = 0


class StampingProcessFeeBatchDeleteResultVO(BaseModel):
    """按条件批量删除结果"""

    deleted_count: int = 0
    skipped_approved_count: int = 0
    year: int
    location: str
    stamping_supplier: str


class StampingProcessFeeBatchAuditResultVO(BaseModel):
    """按条件批量审核 / 反审核结果"""

    updated_count: int = 0
    skipped_count: int = 0
    year: int
    location: str
    stamping_supplier: str
