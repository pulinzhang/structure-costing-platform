"""
冲压零件 VO - 返回给前端的数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_serializer, field_validator

from app.common.money import Q2, Q4, format_money, optional_format_money, quantize_money


def datetime_to_str(value: Union[datetime, str, None]) -> Optional[str]:
    """datetime 类型转字符串序列化器"""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value


# ==================== 冲次单价 VO ====================

class StampingPartResponse(BaseModel):
    """冲压零件响应 VO"""

    model_config = {"from_attributes": True}

    id: int
    location: str
    vehicle_model: str
    version: str
    stamping_supplier: str
    seq_no: Optional[int] = None
    part_number: str
    part_name: Optional[str] = None
    material: Optional[str] = None
    thickness: Optional[Decimal] = None
    part_weight: Optional[Decimal] = None
    sheet_length: Optional[Decimal] = None
    sheet_width: Optional[Decimal] = None
    parts_per_sheet: Optional[int] = Field(
        default=None,
        description=(
            "可制件数：一张钢板/料片单独冲本零件可出的件数"
            "（例：1出2记2；左右共模按单侧计则为2；非利用率百分比）"
        ),
    )
    sheet_type: Optional[str] = None
    die_type: Optional[str] = None
    process_method: Optional[str] = None
    automation: Optional[str] = Field(
        default=None,
        description="自动化：工艺文件原文（如自动/手动/半自动），非布尔是/否",
    )
    remark: Optional[str] = None
    sketch_url: Optional[str] = None
    excel_filename: Optional[str] = None
    excel_sheet_name: Optional[str] = Field(
        default=None, description="来源 Excel 工作表名"
    )
    excel_row: Optional[int] = Field(
        default=None, description="来源 Excel 行号（1-based）"
    )
    excel_part_col: Optional[int] = Field(
        default=None, description="零件号所在列号（1-based）"
    )
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: Any) -> Any:
        return datetime_to_str(value)

    @field_serializer("thickness", "part_weight")
    def serialize_physical(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("sheet_length", "sheet_width")
    def serialize_sheet_dim(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)


class StampingPartListResponse(BaseModel):
    """冲压零件列表项 VO（精简字段，含工序统计数）"""

    model_config = {"from_attributes": True}

    id: int
    vehicle_model: str
    version: str
    part_number: str
    part_name: Optional[str] = None
    material: Optional[str] = None
    thickness: Optional[Decimal] = None
    part_weight: Optional[Decimal] = None
    stamping_supplier: str
    die_type: Optional[str] = None
    process_method: Optional[str] = None
    location: Optional[str] = None
    excel_filename: Optional[str] = None
    excel_sheet_name: Optional[str] = None
    excel_row: Optional[int] = None
    excel_part_col: Optional[int] = None
    sketch_url: Optional[str] = None
    process_count: int = Field(default=0, description="工序数量")

    @field_serializer("thickness", "part_weight")
    def serialize_physical(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)


class StampingProcessResponse(BaseModel):
    """冲压工序响应 VO"""

    model_config = {"from_attributes": True}

    id: int
    part_id: int
    process_seq: str
    process_order: int
    process_code: Optional[str] = None
    die_sets: int
    tonnage: Optional[int] = None
    cost_ratio: Decimal
    remark: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    @field_serializer("cost_ratio")
    def serialize_cost_ratio(self, value: Decimal) -> str:
        return format_money(value, Q2, 2)


class StampingPartWithProcessesResponse(BaseModel):
    """冲压零件（含工序列表）响应 VO"""

    model_config = {"from_attributes": True}

    id: int
    location: str
    vehicle_model: str
    version: str
    stamping_supplier: str
    seq_no: Optional[int] = None
    part_number: str
    part_name: Optional[str] = None
    material: Optional[str] = None
    thickness: Optional[Decimal] = None
    part_weight: Optional[Decimal] = None
    sheet_length: Optional[Decimal] = None
    sheet_width: Optional[Decimal] = None
    parts_per_sheet: Optional[int] = Field(
        default=None,
        description=(
            "可制件数：一张钢板/料片单独冲本零件可出的件数"
            "（例：1出2记2；左右共模按单侧计则为2；非利用率百分比）"
        ),
    )
    sheet_type: Optional[str] = None
    die_type: Optional[str] = None
    process_method: Optional[str] = None
    automation: Optional[str] = Field(
        default=None,
        description="自动化：工艺文件原文（如自动/手动/半自动），非布尔是/否",
    )
    remark: Optional[str] = None
    sketch_url: Optional[str] = None
    excel_filename: Optional[str] = None
    excel_sheet_name: Optional[str] = Field(
        default=None, description="来源 Excel 工作表名"
    )
    excel_row: Optional[int] = Field(
        default=None, description="来源 Excel 行号（1-based）"
    )
    excel_part_col: Optional[int] = Field(
        default=None, description="零件号所在列号（1-based）"
    )
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    processes: list[StampingProcessResponse] = []

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: Any) -> Any:
        return datetime_to_str(value)

    @field_serializer("thickness", "part_weight")
    def serialize_physical(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("sheet_length", "sheet_width")
    def serialize_sheet_dim(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)


class StampingPartQuery(BaseModel):
    """冲压零件查询参数"""
    location: Optional[str] = Field(None, description="采购基地")
    vehicle_model: Optional[str] = Field(None, description="车型")
    version: Optional[str] = Field(None, description="版本")
    part_number: Optional[str] = Field(None, description="零件号")
    part_name: Optional[str] = Field(None, description="零件名称")
    material: Optional[str] = Field(None, description="材质")
    stamping_supplier: Optional[str] = Field(None, description="冲压供应商")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=500, description="每页条数")


class StampingProcessUpdate(BaseModel):
    """工序更新请求"""
    cost_ratio: Optional[Decimal] = Field(
        None, ge=0, le=10, description="成本系数（0~10，即0%~1000%）"
    )
    remark: Optional[str] = None

    @field_validator("cost_ratio", mode="before")
    @classmethod
    def _coerce_cost_ratio(cls, value: Any) -> Decimal | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return quantize_money(value, Q2)


class StampingProcessItemUpdate(BaseModel):
    """单个工序更新项"""
    id: int
    cost_ratio: Optional[Decimal] = Field(
        None, ge=0, le=10, description="成本系数（0~10，即0%~1000%）"
    )
    remark: Optional[str] = None

    @field_validator("cost_ratio", mode="before")
    @classmethod
    def _coerce_cost_ratio(cls, value: Any) -> Decimal | None:
        if value is None or (isinstance(value, str) and not value.strip()):
            return None
        return quantize_money(value, Q2)


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
    summary: Optional[StampingPartListSummaryVO] = None


class StampingCascadeFilterQuery(BaseModel):
    """冲压级联筛选查询参数"""
    location: Optional[str] = Field(None, description="采购基地")
    stamping_supplier: Optional[str] = Field(None, description="冲压工厂")
    vehicle_model: Optional[str] = Field(None, description="配套车型")


class StampingCascadeFilterOptionsVO(BaseModel):
    """冲压级联筛选下拉选项 VO（基地 → 冲压工厂 → 配套车型）"""
    locations: list[str] = Field(default_factory=list, description="基地")
    stamping_suppliers: list[str] = Field(default_factory=list, description="冲压工厂")
    vehicle_models: list[str] = Field(default_factory=list, description="配套车型")
    versions: list[str] = Field(default_factory=list, description="版本")


class StampingMaterialResponse(BaseModel):
    """
    材料信息 VO（去重后的 material + 料厚 + 长/宽）。

    普通件为格式化数值字符串；拼焊件按子片顺序用 ``/`` 拼接，
    如厚度 ``0.70/1.00``、长 ``550.00/555.00``。
    """

    material: Optional[str] = None
    thickness: Optional[str] = Field(
        default=None, description="料厚(mm)；拼焊件为各子片拼接，如 0.70/1.00"
    )
    sheet_length: Optional[str] = Field(
        default=None, description="料片长/卷料宽(mm)；拼焊件为各子片拼接"
    )
    sheet_width: Optional[str] = Field(
        default=None, description="料片宽/卷料步距(mm)；拼焊件为各子片拼接"
    )


class StampingMaterialQuery(BaseModel):
    """材料查询参数"""
    location: Optional[str] = Field(None, description="采购基地")
    stamping_supplier: Optional[str] = Field(None, description="冲压供应商")
    vehicle_model: Optional[str] = Field(None, description="车型")
    version: Optional[str] = Field(None, description="版本")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(50, ge=1, le=500, description="每页条数")


class BatchUpdateResponse(BaseModel):
    """批量更新响应 VO"""
    updated: int


class StampingPartBatchDeleteResultVO(BaseModel):
    """零件批量删除结果 VO"""

    location: str
    stamping_supplier: str
    vehicle_model: str
    version: str
    deleted_count: int = 0
