"""
冲压零件 VO - 返回给前端的数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.common.money import Q2, Q4, format_money, optional_format_money
from app.common.timezone import datetime_to_iso

# ==================== 冲次单价 VO ====================


class StampingPartResponse(BaseModel):
    """冲压零件响应 VO"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    location: str
    vehicle_model: str
    version: str
    stamping_supplier: str
    seq_no: int | None = None
    part_number: str
    part_name: str | None = None
    material: str | None = None
    thickness: Decimal | None = None
    part_weight: Decimal | None = None
    sheet_length: Decimal | None = None
    sheet_width: Decimal | None = None
    parts_per_sheet: int | None = Field(
        default=None,
        description=(
            "可制件数：一张钢板/料片单独冲本零件可出的件数"
            "（例：1出2记2；左右共模按单侧计则为2；非利用率百分比）"
        ),
    )
    sheet_type: str | None = None
    is_offal_nested: bool = False
    offal_source: str | None = None
    is_scrap_byproduct: bool = False
    has_swing_shear: bool = False
    die_type: str | None = None
    process_method: str | None = None
    automation: str | None = Field(
        default=None,
        description="自动化：工艺文件原文（如自动/手动/半自动），非布尔是/否",
    )
    remark: str | None = None
    sketch_url: str | None = None
    excel_filename: str | None = None
    excel_sheet_name: str | None = Field(default=None, description="来源 Excel 工作表名")
    excel_row: int | None = Field(default=None, description="来源 Excel 行号（1-based）")
    excel_part_col: int | None = Field(default=None, description="零件号所在列号（1-based）")
    effective_year: int | None = None
    effective_month: int | None = None
    expiry_year: int | None = None
    expiry_month: int | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: Any) -> Any:
        return datetime_to_iso(value)

    @field_serializer("thickness", "part_weight")
    def serialize_physical(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("sheet_length", "sheet_width")
    def serialize_sheet_dim(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)


class StampingPartListResponse(BaseModel):
    """冲压零件列表项 VO（精简字段，含工序统计数）"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_model: str
    version: str
    part_number: str
    part_name: str | None = None
    material: str | None = None
    thickness: Decimal | None = None
    part_weight: Decimal | None = None
    stamping_supplier: str
    die_type: str | None = None
    process_method: str | None = None
    location: str | None = None
    is_offal_nested: bool = False
    offal_source: str | None = None
    is_scrap_byproduct: bool = False
    has_swing_shear: bool = False
    excel_filename: str | None = None
    excel_sheet_name: str | None = None
    excel_row: int | None = None
    excel_part_col: int | None = None
    sketch_url: str | None = None
    process_count: int = Field(default=0, description="工序数量")
    effective_year: int | None = None
    effective_month: int | None = None
    expiry_year: int | None = None
    expiry_month: int | None = None

    @field_serializer("thickness", "part_weight")
    def serialize_physical(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)


class StampingProcessResponse(BaseModel):
    """冲压工序响应 VO"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    process_seq: str
    process_order: int
    process_code: str | None = None
    die_sets: int
    die_number: str | None = None
    tonnage: int | None = None
    cost_ratio: Decimal
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None

    @field_serializer("cost_ratio")
    def serialize_cost_ratio(self, value: Decimal) -> str:
        return format_money(value, Q2, 2)


class StampingPartMaterialChangeResponse(BaseModel):
    """零件明细里的一刀材料变更。有效止是下一刀的前一月。"""

    effective_year: int
    effective_month: int
    valid_until_year: int | None = None
    valid_until_month: int | None = None
    before_material: str
    after_material: str
    before_thickness: Decimal
    after_thickness: Decimal

    @field_serializer("before_thickness", "after_thickness")
    def serialize_thickness(self, value: Decimal) -> str:
        return format_money(value, Q4, 4)


class StampingPartWithProcessesResponse(BaseModel):
    """冲压零件（含工序列表）响应 VO"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    location: str
    vehicle_model: str
    version: str
    stamping_supplier: str
    seq_no: int | None = None
    part_number: str
    part_name: str | None = None
    material: str | None = None
    thickness: Decimal | None = None
    part_weight: Decimal | None = None
    sheet_length: Decimal | None = None
    sheet_width: Decimal | None = None
    parts_per_sheet: int | None = Field(
        default=None,
        description=(
            "可制件数：一张钢板/料片单独冲本零件可出的件数"
            "（例：1出2记2；左右共模按单侧计则为2；非利用率百分比）"
        ),
    )
    sheet_type: str | None = None
    is_offal_nested: bool = False
    offal_source: str | None = None
    is_scrap_byproduct: bool = False
    has_swing_shear: bool = False
    die_type: str | None = None
    process_method: str | None = None
    automation: str | None = Field(
        default=None,
        description="自动化：工艺文件原文（如自动/手动/半自动），非布尔是/否",
    )
    remark: str | None = None
    sketch_url: str | None = None
    excel_filename: str | None = None
    excel_sheet_name: str | None = Field(default=None, description="来源 Excel 工作表名")
    excel_row: int | None = Field(default=None, description="来源 Excel 行号（1-based）")
    excel_part_col: int | None = Field(default=None, description="零件号所在列号（1-based）")
    effective_year: int | None = None
    effective_month: int | None = None
    expiry_year: int | None = None
    expiry_month: int | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    processes: list[StampingProcessResponse] = []
    material_changes: list[StampingPartMaterialChangeResponse] = []

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: Any) -> Any:
        return datetime_to_iso(value)

    @field_serializer("thickness", "part_weight")
    def serialize_physical(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("sheet_length", "sheet_width")
    def serialize_sheet_dim(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)


class StampingPartListSummaryVO(BaseModel):
    """列表筛选汇总（去重：基地 / 冲压工厂 / 车型 / 零件号 / 版本）"""

    location_count: int = 0
    stamping_supplier_count: int = 0
    vehicle_model_count: int = 0
    part_number_count: int = 0
    version_count: int = 0


class StampingPartListFilterOptions(BaseModel):
    """零件列表筛选下拉选项 VO"""

    locations: list[str] = []
    vehicle_models: list[str] = []
    versions: list[str] = []
    materials: list[str] = []
    stamping_suppliers: list[str] = []
    summary: StampingPartListSummaryVO | None = None


class StampingCascadeFilterOptionsVO(BaseModel):
    """冲压级联筛选下拉选项 VO（基地 → 车型 → 版本 → 冲压工厂）"""

    locations: list[str] = Field(default_factory=list, description="基地")
    stamping_suppliers: list[str] = Field(default_factory=list, description="冲压工厂")
    vehicle_models: list[str] = Field(default_factory=list, description="项目")
    versions: list[str] = Field(default_factory=list, description="版本")


def _join_decimal_texts(values: list[Decimal], quant: Decimal, places: int) -> str | None:
    """按顺序格式化后用 / 拼接；空列表则 None（JSON 仍是字符串）。"""
    if not values:
        return None
    return "/".join(format_money(value, quant, places) for value in values)


class StampingMaterialResponse(BaseModel):
    """
    材料信息 VO（去重后的 material + 料厚 + 长/宽）。

    Service 传入 Decimal 列表；JSON 由 serializer 输出字符串。
    普通件为格式化数值；拼焊件按子片顺序用 ``/`` 拼接，
    如厚度 ``0.70/1.00``、长 ``550.00/555.00``。
    """

    material: str | None = None
    thickness: list[Decimal] = Field(
        default_factory=list, description="料厚(mm)；拼焊件为各子片，JSON 拼接如 0.70/1.00"
    )
    sheet_length: list[Decimal] = Field(
        default_factory=list, description="料片长/卷料宽(mm)；拼焊件为各子片"
    )
    sheet_width: list[Decimal] = Field(
        default_factory=list, description="料片宽/卷料步距(mm)；拼焊件为各子片"
    )

    @field_serializer("thickness")
    def serialize_thickness(self, values: list[Decimal]) -> str | None:
        if len(values) >= 2:
            return _join_decimal_texts(values, Q2, 2)
        return _join_decimal_texts(values, Q4, 4)

    @field_serializer("sheet_length", "sheet_width")
    def serialize_sheet_dims(self, values: list[Decimal]) -> str | None:
        return _join_decimal_texts(values, Q2, 2)


class BatchUpdateResponse(BaseModel):
    """批量更新响应 VO"""

    updated: int
    message: str = ""


class StampingPartBatchDeleteResultVO(BaseModel):
    """零件批量删除结果 VO"""

    location: str
    stamping_supplier: str | None = None
    vehicle_model: str
    version: str
    deleted_count: int = 0
