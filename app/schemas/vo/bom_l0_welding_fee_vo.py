"""
BOM 焊接费 VO - 响应数据结构
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer

from app.common.money import Q4, optional_format_money


class BomL0WeldingFeeItemVO(BaseModel):
    """焊接费工艺明细行"""

    id: int | None = None
    line_no: int
    process_token: str | None = None
    standard_process_name: str | None = None
    process_qty: Decimal
    process_qty_unit: str | None = None
    unit_price: Decimal | None = None
    unit: str | None = None
    line_fee: Decimal | None = None
    match_status: str = "unmapped"
    source_breakdown_line_id: int | None = None
    remark: str | None = None

    @field_serializer("process_qty", "unit_price", "line_fee")
    def serialize_money(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    model_config = {"from_attributes": True}


class BomL0WeldingFeeVO(BaseModel):
    """焊接费结果行"""

    id: int
    year: int
    location: str
    vehicle_model: str
    bom_version: str
    source_breakdown_node_id: int | None = None
    part_number: str
    part_name: str | None = None
    customer_name: str | None = None
    weld_info_raw: str | None = None
    process_line_count: int = 0
    matched_line_count: int = 0
    missing_price_count: int = 0
    total_l0_welding_fee: Decimal
    calc_batch_id: str | None = None
    calc_status: str = "ok"
    calc_message: str | None = None
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
    items: list[BomL0WeldingFeeItemVO] = Field(default_factory=list)

    @field_serializer("total_l0_welding_fee")
    def serialize_fee(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer(
        "created_at",
        "updated_at",
        "audited_at",
        "reverse_audited_at",
    )
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    model_config = {"from_attributes": True}


class BomL0WeldingFeeCalcReadyVO(BaseModel):
    """计算前数据就绪统计"""

    year: int
    location: str
    vehicle_model: str
    bom_version: str
    l0_count: int = 0
    unit_price_count: int = 0
    l0_process_line_total: int = 0
    zero_process_l0_count: int = 0


class BomL0WeldingFeeCalcResultVO(BaseModel):
    """焊接费计算汇总（异步任务完成后的 result）"""

    year: int
    location: str
    vehicle_model: str
    bom_version: str
    calc_batch_id: str | None = None
    log_id: int | None = None
    status: str = "success"
    l0_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    skipped_approved_count: int = 0
    failed_count: int = 0
    missing_price_count: int = 0
    detail_text: str = ""
    started_at: str | None = None
    finished_at: str | None = None


class BomL0WeldingFeeCalcLogVO(BaseModel):
    """计算历史行"""

    model_config = {"from_attributes": True}

    id: int
    calc_batch_id: str
    year: int
    location: str
    vehicle_model: str
    bom_version: str
    status: str
    l0_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    skipped_approved_count: int = 0
    failed_count: int = 0
    missing_price_count: int = 0
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


class BomL0WeldingFeeBatchAuditResultVO(BaseModel):
    """按条件批量审核 / 反审核结果"""

    updated_count: int = 0
    skipped_count: int = 0
    year: int
    location: str
    vehicle_model: str
    bom_version: str


class BomL0WeldingFeeBatchDeleteResultVO(BaseModel):
    """按条件批量删除结果"""

    deleted_count: int = 0
    skipped_approved_count: int = 0
    year: int
    location: str
    vehicle_model: str
    bom_version: str
