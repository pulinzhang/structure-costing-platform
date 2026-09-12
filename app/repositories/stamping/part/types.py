"""冲压零件 Repository 的查询结果形状。"""

from __future__ import annotations

from decimal import Decimal
from typing import TypedDict


class StampingPartFilterOptionValues(TypedDict):
    """筛选下拉选项（不含列表汇总，汇总由 Service 拼入）。"""

    locations: list[str]
    stamping_suppliers: list[str]
    vehicle_models: list[str]
    versions: list[str]
    materials: list[str]


class MaterialSpecRow(TypedDict):
    """去重后的材料规格行（钢价 Step1）。"""

    location: str
    material: str
    thickness: Decimal


class StampingPartScopeIdentity(TypedDict):
    """基地+项目下去重后的零件号与名称。"""

    part_number: str
    part_name: str


class StampingPartDieMatchIdentity(TypedDict):
    """基地+项目下工艺零件身份（布点回填供应商/版本）。"""

    part_number: str
    stamping_supplier: str
    version: str
