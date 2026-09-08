"""
BOM 焊接费 VO - 响应数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from pydantic import BaseModel, Field, field_serializer

from app.common.money import Q4, format_money, optional_format_money
from app.common.timezone import datetime_to_iso
from app.schemas.common.batch_result import BatchAuditCountsVO, BatchDeleteCountsVO


class BomWeldingFeeItemVO(BaseModel):
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


class BomWeldingFeeVO(BaseModel):
    """焊接费结果行"""

    id: int
    year: int
    location: str
    vehicle_model: str
    bom_version: str
    level: int = 0
    source_breakdown_node_id: int | None = None
    part_number: str
    part_name: str | None = None
    customer_name: str | None = None
    weld_info_raw: str | None = None
    process_line_count: int = 0
    matched_line_count: int = 0
    missing_price_count: int = 0
    total_welding_fee: Decimal
    other_fee: Decimal | None = None
    final_welding_fee: Decimal | None = None
    remark: str | None = None
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
    items: list[BomWeldingFeeItemVO] = Field(default_factory=list)

    @field_serializer("total_welding_fee", "other_fee", "final_welding_fee")
    def serialize_fee(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer(
        "created_at",
        "updated_at",
        "audited_at",
        "reverse_audited_at",
    )
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    model_config = {"from_attributes": True}


class WeldingFeeLevelReadyVO(BaseModel):
    """计算就绪：某一树层级的节点统计。"""

    level: int
    node_count: int = 0
    process_line_total: int = 0
    zero_process_count: int = 0


class BomWeldingFeeCalcReadyVO(BaseModel):
    """计算前数据就绪统计"""

    year: int
    location: str
    vehicle_model: str
    bom_version: str
    unit_price_count: int = 0
    levels: list[WeldingFeeLevelReadyVO] = Field(default_factory=list)


class BomWeldingFeeCalcResultVO(BaseModel):
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


class BomWeldingFeeCalcLogVO(BaseModel):
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
        return datetime_to_iso(value)


class WeldingFeeListSummaryVO(BaseModel):
    """列表 HUD 汇总：按筛选条件全量聚合，不含分页、不含缺单价钻取。"""

    total_count: int = 0
    total_fee: Decimal = Decimal("0")
    pending_count: int = 0
    approved_count: int = 0
    partial_count: int = 0
    failed_count: int = 0
    missing_price_count: int = 0

    @field_serializer("total_fee")
    def serialize_total_fee(self, value: Decimal) -> str:
        return format_money(value, Q4, 4)


class WeldingFeeListApiFilters(TypedDict):
    """列表响应 filters：查询回显 + HUD 全量汇总。"""

    year: int | None
    location: str | None
    vehicle_model: str | None
    bom_version: str | None
    part_number: str | None
    audit_status: str | None
    calc_status: str | None
    level: int | None
    levels: list[int] | None
    summary: WeldingFeeListSummaryVO


class BomWeldingFeeBatchAuditResultVO(BatchAuditCountsVO):
    """按条件批量审核 / 反审核结果"""

    year: int
    location: str
    vehicle_model: str
    bom_version: str


class BomWeldingFeeBatchDeleteResultVO(BatchDeleteCountsVO):
    """按条件批量删除结果"""

    year: int
    location: str
    vehicle_model: str
    bom_version: str
