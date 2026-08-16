"""
钢材价格 VO - 返回给前端的数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_serializer

from app.common.money import Q4, format_money, optional_format_money


def datetime_to_str(value: datetime | None) -> Optional[str]:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class SteelPriceListSummaryVO(BaseModel):
    """列表筛选汇总（均价 / 待审 / 已审，按过滤条件全量）"""

    avg_final_price: Optional[Decimal] = None
    pending_count: int = 0
    approved_count: int = 0

    @field_serializer("avg_final_price")
    def serialize_avg_final_price(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)


class SteelPriceFilterOptions(BaseModel):
    """列表筛选选项"""

    years: list[int] = []
    months: list[int] = []
    locations: list[str] = []
    category_names: list[str] = []
    steel_mills: list[str] = []
    audit_statuses: list[str] = []
    summary: Optional[SteelPriceListSummaryVO] = None


class SteelPriceBatchDeleteResultVO(BaseModel):
    """按条件批量删除结果"""

    deleted_count: int = 0
    skipped_approved_count: int = 0
    year: int
    month: int
    location: str


class SteelPriceBatchAuditResultVO(BaseModel):
    """按条件批量审核 / 反审核结果"""

    updated_count: int = 0
    skipped_count: int = 0
    year: int
    month: int
    location: str


class SteelPriceResponse(BaseModel):
    """钢材价格响应 VO"""

    model_config = {"from_attributes": True}

    id: int
    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thickness: Decimal
    width: Decimal
    spec: Optional[str] = None

    base_price: Decimal
    thickness_adjustment: Decimal
    width_adjustment: Decimal
    zinc_adjustment: Decimal
    processing_fee: Decimal
    other_adjustment: Decimal
    final_price_per_ton: Decimal

    base_price_id: Optional[int] = None
    base_excel_filename: Optional[str] = None
    base_sheet_name: Optional[str] = None
    base_excel_row: Optional[int] = None
    base_excel_col: Optional[int] = None

    thickness_policy_id: Optional[int] = None
    thickness_ladder_item_id: Optional[int] = None
    thickness_excel_filename: Optional[str] = None
    thickness_sheet_name: Optional[str] = None
    thickness_excel_row: Optional[int] = None
    thickness_excel_col: Optional[int] = None

    width_policy_id: Optional[int] = None
    width_ladder_item_id: Optional[int] = None
    width_excel_filename: Optional[str] = None
    width_sheet_name: Optional[str] = None
    width_excel_row: Optional[int] = None
    width_excel_col: Optional[int] = None

    zinc_policy_id: Optional[int] = None
    zinc_ladder_item_id: Optional[int] = None
    zinc_excel_filename: Optional[str] = None
    zinc_sheet_name: Optional[str] = None
    zinc_excel_row: Optional[int] = None
    zinc_excel_col: Optional[int] = None

    calc_batch_id: str
    match_status: str
    calc_status: str
    calc_message: Optional[str] = None
    formula_version: str
    calculated_at: Optional[datetime] = None

    audit_status: str
    audited_by: Optional[str] = None
    audited_at: Optional[datetime] = None
    audit_remark: Optional[str] = None
    reverse_audited_by: Optional[str] = None
    reverse_audited_at: Optional[datetime] = None
    reverse_audit_remark: Optional[str] = None

    remark: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("thickness")
    def serialize_thickness(self, value: Decimal) -> str:
        return format_money(value, Q4, 4)

    @field_serializer("width")
    def serialize_width(self, value: Decimal) -> str:
        return format_money(value, Q4, 4)

    @field_serializer("base_price", "processing_fee", "final_price_per_ton")
    def serialize_price(self, value: Decimal) -> str:
        return format_money(value, Q4, 4)

    @field_serializer(
        "thickness_adjustment",
        "width_adjustment",
        "zinc_adjustment",
        "other_adjustment",
    )
    def serialize_adjustment(self, value: Decimal) -> str:
        return format_money(value, Q4, 4, allow_negative=True)

    @field_serializer(
        "calculated_at",
        "audited_at",
        "reverse_audited_at",
        "created_at",
        "updated_at",
    )
    def serialize_datetime(self, value: datetime | None) -> Optional[str]:
        return datetime_to_str(value)


class SteelPriceCalcResultVO(BaseModel):
    """钢价批量计算落库结果摘要 VO"""

    model_config = {"from_attributes": True}

    calc_batch_id: str
    log_id: Optional[int] = None
    status: str = "failed"
    year: Optional[int] = None
    month: Optional[int] = None
    location: Optional[str] = None
    stamping_supplier: Optional[str] = None
    vehicle_model: Optional[str] = None
    material_count: int = 0
    enriched_count: int = 0
    no_base_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    skipped_approved_count: int = 0
    failed_count: int = 0
    detail_text: str = ""
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class SteelPriceCalcLogVO(BaseModel):
    """钢价计算历史记录 VO（含 detail_text 全过程）"""

    model_config = {"from_attributes": True}

    id: int
    calc_batch_id: str
    year: int
    month: int
    location: str
    stamping_supplier: Optional[str] = None
    vehicle_model: Optional[str] = None
    status: str
    material_count: int = 0
    enriched_count: int = 0
    no_base_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    skipped_approved_count: int = 0
    failed_count: int = 0
    detail_text: str = ""
    operator_id: Optional[int] = None
    operator_name: Optional[str] = None
    created_by: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @field_serializer("started_at", "finished_at", "created_at")
    def serialize_datetime(self, value: datetime | None) -> Optional[str]:
        return datetime_to_str(value)
