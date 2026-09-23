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
    """去重后的材料规格行（钢价 Step1 统计仍用，无年月）。"""

    location: str
    material: str
    thickness: Decimal


class MaterialAsOfIdentity(TypedDict):
    """普通件身份，交给当月材料解析。"""

    part_id: int
    location: str
    stamping_supplier: str
    vehicle_model: str
    part_number: str
    material: str


class MaterialAsOfRow(TypedDict):
    """该月取材质一行。blank_id 空 = 零件行。"""

    part_id: int
    location: str
    material: str
    thickness: Decimal | None
    blank_id: int | None


class StampingPartScopeIdentity(TypedDict):
    """基地+项目下去重后的零件号与名称。"""

    part_number: str
    part_name: str


class StampingPartDieMatchIdentity(TypedDict):
    """基地+项目下工艺零件身份（布点回填供应商/版本）。"""

    part_number: str
    stamping_supplier: str
    version: str
