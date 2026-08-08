"""
钢材基准价格 VO - 返回给前端的数据结构
"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, field_validator


class SteelBasePriceResponse(BaseModel):
    """钢材基准价格响应 VO"""

    model_config = {"from_attributes": True}

    id: int
    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thick: Optional[Any] = None  # Decimal or str
    width: Optional[Any] = None  # Decimal or str
    base_price: Optional[Any] = None  # Decimal or str
    processing_fee: Optional[Any] = None  # Decimal or str
    excel_filename: Optional[str] = None
    sheet_name: Optional[str] = None
    excel_row: Optional[int] = None
    excel_col: Optional[int] = None
    remark: Optional[str] = None
    created_at: Optional[Any] = None  # datetime
    updated_at: Optional[Any] = None  # datetime
