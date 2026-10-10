"""
拼焊子片 VO - API / Service 输出
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.common.money import Q2, Q4, optional_format_money
from app.common.timezone import datetime_to_iso


class StampingTailorWeldBlankVO(BaseModel):
    """拼焊子片响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    parent_part_number: str
    blank_seq: int
    blank_part_number: str
    material: str | None = None
    thickness: Decimal | None = None
    part_weight: Decimal | None = None
    sheet_length: Decimal | None = None
    sheet_width: Decimal | None = None
    parts_per_sheet: int | None = Field(
        default=None,
        description="可制件数：一张料单独冲本子片可出的件数",
    )
    sheet_type: str | None = None
    remark: str | None = None
    created_by: str | None = None
    updated_by: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)

    @field_serializer("thickness", "part_weight")
    def serialize_physical(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("sheet_length", "sheet_width")
    def serialize_sheet_dim(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)
