"""
拼焊子片 VO - API / Service 输出
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_serializer

from app.common.money import Q2, Q4, optional_format_money
from app.common.timezone import datetime_to_iso


class StampingTailorWeldBlankVO(BaseModel):
    """拼焊子片响应。"""

    model_config = {"from_attributes": True}

    id: int
    part_id: int
    parent_part_number: str
    blank_seq: int
    blank_part_number: str
    material: Optional[str] = None
    thickness: Optional[Decimal] = None
    part_weight: Optional[Decimal] = None
    sheet_length: Optional[Decimal] = None
    sheet_width: Optional[Decimal] = None
    parts_per_sheet: Optional[int] = Field(
        default=None,
        description="可制件数：一张料单独冲本子片可出的件数",
    )
    sheet_type: Optional[str] = None
    remark: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: Any) -> Any:
        return datetime_to_iso(value)

    @field_serializer("thickness", "part_weight")
    def serialize_physical(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("sheet_length", "sheet_width")
    def serialize_sheet_dim(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)
