"""零件用在哪 — 查询入参。"""

from typing import Literal

from pydantic import BaseModel, Field


class BomWhereUsedQuery(BaseModel):
    """零件用在哪查询。字段名 query 走 Depends()，不要拆成 Query() 参数。"""

    query: str = Field(..., min_length=1, description="零件号、短码、名称或内部号")
    match: Literal["part", "internal_number"] = Field("part", description="零件模糊 / 内部号精确")
    location: str | None = Field(None, description="采购基地")
    vehicle_model: str | None = Field(None, description="项目")
    bom_version: str | None = Field(None, description="材料清单版本")
    status: str = Field("active", description="清单状态；all 表示不限")
    depth: Literal["single", "multi"] = Field("multi", description="单层或到 L0")
