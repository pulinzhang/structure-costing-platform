"""中标钢厂厚度价格列表 VO。"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer

from app.common.money import Q2, Q4, format_money, optional_format_money


class WinningThicknessRowVO(BaseModel):
    """中标钢材 × 厚度阶梯 导出/预览行。"""

    model_config = ConfigDict(from_attributes=True)

    # 价目
    base_price: Decimal
    thickness_adjustment: Decimal
    processing_fee: Decimal = Decimal("0")
    final_price: Decimal

    # 业务维度
    category_name: str
    steel_mill: str
    steel_mill_id: int = 0
    thickness_range: str
    thick_min: Decimal | None = None
    thick_min_operator: str | None = None
    thick_max: Decimal | None = None
    thick_max_operator: str | None = None
    grade: str
    year: int
    month: int
    location: str
    spec: str | None = None
    base_thickness: Decimal | None = None

    # 基价溯源
    base_price_id: int | None = None
    base_excel_filename: str | None = None
    base_sheet_name: str | None = None
    base_excel_row: int | None = None
    base_excel_col: int | None = None

    # 厚度政策溯源
    thickness_policy_id: int | None = None
    thickness_ladder_item_id: int | None = None
    thickness_excel_filename: str | None = None
    thickness_excel_row: int | None = None
    thickness_excel_col: int | None = None

    @field_serializer("base_price", "processing_fee", "final_price")
    def serialize_price(self, value: Decimal) -> str:
        return format_money(value, Q4, 4)

    @field_serializer("thickness_adjustment")
    def serialize_adjustment(self, value: Decimal) -> str:
        return format_money(value, Q4, 4, allow_negative=True)

    @field_serializer("base_thickness", "thick_min", "thick_max")
    def serialize_thickness(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)
