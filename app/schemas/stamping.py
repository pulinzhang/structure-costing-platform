"""
冲压工艺查询 DTO
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Union
from pydantic import BaseModel, Field, field_serializer


def decimal_to_float(value: Union[Decimal, float, None]) -> float | None:
    """Decimal 类型转 float 序列化器工厂"""
    return float(value) if isinstance(value, Decimal) else value


class StampingPartQuery(BaseModel):
    """零件查询参数"""
    vehicle_model: Optional[str] = Field(None, description="车型")
    version: Optional[str] = Field(None, description="版本")
    part_number: Optional[str] = Field(None, description="零件号")
    part_name: Optional[str] = Field(None, description="零件名称")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(10, ge=1, le=500, description="每页条数")


class StampingProcessResponse(BaseModel):
    """工序响应"""
    id: int
    part_id: int
    process_seq: str | None
    process_order: int
    process_code: str | None
    die_sets: int | None
    tonnage: int | None
    cost_ratio: float
    remark: str | None
    created_at: datetime | None

    @field_serializer("cost_ratio")
    def serialize_cost_ratio(self, value: Union[Decimal, float]) -> float:
        return decimal_to_float(value)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    model_config = {"from_attributes": True}


class StampingPartBaseResponse(BaseModel):
    """零件基础响应字段（被列表和详情响应共用）"""
    id: int
    vehicle_model: str
    version: str
    seq_no: int | None
    part_number: str
    part_name: str | None
    material: str | None
    thickness: float | None
    part_weight: float | None
    sheet_length: float | None
    sheet_width: float | None
    parts_per_sheet: int | None
    sheet_type: str | None
    tonnage: float | None
    die_type: str | None
    process_method: str | None
    automation: str | None
    remark: str | None
    sketch_url: str | None
    created_at: datetime | None
    updated_at: datetime | None

    @field_serializer("thickness", "part_weight", "sheet_length", "sheet_width", "tonnage")
    def serialize_decimal(self, value: Union[Decimal, float, None]) -> float | None:
        return decimal_to_float(value)

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None

    model_config = {"from_attributes": True}


class StampingPartListResponse(StampingPartBaseResponse):
    """零件列表响应（不包含工序详情，避免 N+1 与冗余数据）"""
    process_count: int = 0


class StampingPartResponse(StampingPartBaseResponse):
    """零件响应（包含完整工序详情）"""
    processes: List[StampingProcessResponse] = []
