"""
钢材价格 VO - 返回给前端的数据结构
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_serializer

from app.common.money import Q4, format_money, optional_format_money
from app.common.timezone import datetime_to_iso
from app.schemas.common.batch_result import BatchAuditCountsVO, BatchDeleteCountsVO


class SteelPriceListSummaryVO(BaseModel):
    """列表筛选汇总（均价 / 待审 / 已审，按过滤条件全量）"""

    avg_final_price: Decimal | None = None
    pending_count: int = 0
    approved_count: int = 0

    @field_serializer("avg_final_price")
    def serialize_avg_final_price(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)


class SteelPriceFilterOptionsVO(BaseModel):
    """列表筛选选项"""

    years: list[int] = []
    months: list[int] = []
    locations: list[str] = []
    category_names: list[str] = []
    steel_mills: list[str] = []
    audit_statuses: list[str] = []
    summary: SteelPriceListSummaryVO | None = None


class SteelPriceBatchDeleteResultVO(BatchDeleteCountsVO):
    """按条件批量删除结果"""

    year: int
    month: int
    location: str


class SteelPriceBatchAuditResultVO(BatchAuditCountsVO):
    """按条件批量审核 / 反审核结果"""

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
    spec: str | None = None

    base_price: Decimal
    thickness_adjustment: Decimal
    width_adjustment: Decimal
    zinc_adjustment: Decimal
    processing_fee: Decimal
    other_adjustment: Decimal
    final_price_per_ton: Decimal

    base_price_id: int | None = None
    base_excel_filename: str | None = None
    base_sheet_name: str | None = None
    base_excel_row: int | None = None
    base_excel_col: int | None = None

    thickness_policy_id: int | None = None
    thickness_ladder_item_id: int | None = None
    thickness_excel_filename: str | None = None
    thickness_sheet_name: str | None = None
    thickness_excel_row: int | None = None
    thickness_excel_col: int | None = None

    width_policy_id: int | None = None
    width_ladder_item_id: int | None = None
    width_excel_filename: str | None = None
    width_sheet_name: str | None = None
    width_excel_row: int | None = None
    width_excel_col: int | None = None

    zinc_policy_id: int | None = None
    zinc_ladder_item_id: int | None = None
    zinc_excel_filename: str | None = None
    zinc_sheet_name: str | None = None
    zinc_excel_row: int | None = None
    zinc_excel_col: int | None = None

    calc_batch_id: str
    match_status: str
    calc_status: str
    calc_message: str | None = None
    formula_version: str
    calculated_at: datetime | None = None

    audit_status: str
    audited_by: str | None = None
    audited_at: datetime | None = None
    audit_remark: str | None = None
    reverse_audited_by: str | None = None
    reverse_audited_at: datetime | None = None
    reverse_audit_remark: str | None = None

    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

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
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


class SteelPriceCalcResultVO(BaseModel):
    """钢价批量计算落库结果摘要 VO"""

    model_config = {"from_attributes": True}

    calc_batch_id: str
    log_id: int | None = None
    status: str = "failed"
    year: int | None = None
    month: int | None = None
    location: str | None = None
    material_count: int = 0
    enriched_count: int = 0
    no_base_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    skipped_approved_count: int = 0
    failed_count: int = 0
    detail_text: str = ""
    started_at: str | None = None
    finished_at: str | None = None


class SteelPriceCalcLogVO(BaseModel):
    """钢价计算历史记录 VO（含 detail_text 全过程）"""

    model_config = {"from_attributes": True}

    id: int
    calc_batch_id: str
    year: int
    month: int
    location: str
    status: str
    material_count: int = 0
    enriched_count: int = 0
    no_base_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    skipped_approved_count: int = 0
    failed_count: int = 0
    detail_text: str = ""
    operator_id: int | None = None
    operator_name: str | None = None
    created_by: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None

    @field_serializer("started_at", "finished_at", "created_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)
