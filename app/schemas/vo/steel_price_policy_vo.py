"""
钢价政策 VO - 返回给前端的数据结构
"""

from typing import Optional

from pydantic import BaseModel


class SteelPricePolicyResponse(BaseModel):
    """钢价政策响应 VO"""

    model_config = {"from_attributes": True}

    id: int
    year: int
    month: int
    steel_mill: str
    category_name: str
    policy_type: str
    grade_type: Optional[str] = None
    grade_value: Optional[str] = None
    base_thickness: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SteelPricePolicyItemResponse(BaseModel):
    """钢价政策阶梯明细响应 VO"""

    model_config = {"from_attributes": True}

    id: int
    policy_id: int
    target_sub_group: Optional[str] = None
    thick_min: Optional[str] = None
    thick_min_operator: Optional[str] = None
    thick_max: Optional[str] = None
    thick_max_operator: Optional[str] = None
    width_min: Optional[str] = None
    width_min_operator: Optional[str] = None
    width_max: Optional[str] = None
    width_max_operator: Optional[str] = None
    zinc_coating_min: Optional[str] = None
    zinc_coating_min_operator: Optional[str] = None
    zinc_coating_max: Optional[str] = None
    zinc_coating_max_operator: Optional[str] = None
    price_adjustment: Optional[int] = None
    is_base: Optional[int] = None
    sort_order: Optional[int] = None
