"""
钢材基准价格 VO - 返回给前端的数据结构
"""

from typing import Optional

from pydantic import BaseModel


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
    thick: Optional[str] = None
    width: Optional[str] = None
    base_price: Optional[str] = None
    processing_fee: Optional[str] = None
    excel_filename: Optional[str] = None
    sheet_name: Optional[str] = None
    excel_row: Optional[int] = None
    remark: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
