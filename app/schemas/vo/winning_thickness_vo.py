"""中标钢厂厚度价格一览表 VO。"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_serializer

from app.common.money import Q2, Q4, format_money, optional_format_money


class WinningThicknessRowVO(BaseModel):
    """中标钢材 × 厚度阶梯 导出/预览行。"""

    model_config = {"from_attributes": True}

    # 价目
    base_price: Decimal
    thickness_adjustment: Decimal
    processing_fee: Decimal = Decimal("0")
    final_price: Decimal

    # 业务维度
    category_name: str
    steel_mill: str
    thickness_range: str
    grade: str
    year: int
    month: int
    location: str
    spec: Optional[str] = None
    base_thickness: Optional[Decimal] = None

    # 基价溯源
    base_price_id: Optional[int] = None
    base_excel_filename: Optional[str] = None
    base_sheet_name: Optional[str] = None
    base_excel_row: Optional[int] = None
    base_excel_col: Optional[int] = None

    # 厚度政策溯源
    thickness_policy_id: Optional[int] = None
    thickness_ladder_item_id: Optional[int] = None
    thickness_excel_filename: Optional[str] = None
    thickness_excel_row: Optional[int] = None
    thickness_excel_col: Optional[int] = None

    @field_serializer("base_price", "processing_fee", "final_price")
    def serialize_price(self, value: Decimal) -> str:
        return format_money(value, Q4, 4)

    @field_serializer("thickness_adjustment")
    def serialize_adjustment(self, value: Decimal) -> str:
        return format_money(value, Q4, 4, allow_negative=True)

    @field_serializer("base_thickness")
    def serialize_thickness(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)
