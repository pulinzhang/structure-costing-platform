"""中标材料厚度价格一览 VO。"""

from typing import Optional

from pydantic import BaseModel, field_serializer


class WinningThicknessRowVO(BaseModel):
    """中标钢材 × 厚度阶梯 导出/预览行。"""

    model_config = {"from_attributes": True}

    # 价目
    base_price: float
    thickness_adjustment: float
    processing_fee: float = 0
    final_price: float

    # 业务维度
    category_name: str
    steel_mill: str
    thickness_range: str
    grade: str
    year: int
    month: int
    location: str
    spec: Optional[str] = None
    base_thickness: Optional[float] = None

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

    @field_serializer(
        "base_price",
        "thickness_adjustment",
        "processing_fee",
        "final_price",
        "base_thickness",
    )
    def serialize_float(self, value: float | None) -> float | None:
        if value is None:
            return None
        return float(value)
