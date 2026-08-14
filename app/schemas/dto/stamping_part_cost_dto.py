"""冲压零件价格核算 DTO。"""

from pydantic import BaseModel, Field


class StampingPartCostScopeDTO(BaseModel):
    """范围：年度 + 月份 + 基地 + 冲压工厂。"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    month: int = Field(..., ge=1, le=12, description="月份")
    location: str = Field(..., min_length=1, description="基地")
    stamping_supplier: str = Field(..., min_length=1, description="冲压工厂")


class StampingPartCostCalcDTO(StampingPartCostScopeDTO):
    """计算请求（车型/版本可选）。"""

    vehicle_model: str | None = Field(None, description="车型")
    version: str | None = Field(None, description="版本")


class StampingPartCostQuery(BaseModel):
    """列表查询参数。"""

    year: int | None = Field(None, description="年度")
    month: int | None = Field(None, description="月份")
    location: str | None = Field(None, description="基地")
    stamping_supplier: str | None = Field(None, description="冲压工厂")
    vehicle_model: str | None = Field(None, description="车型")
    version: str | None = Field(None, description="版本")
    part_number: str | None = Field(None, description="零件号")
    audit_status: str | None = Field(None, description="审核状态")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=500, description="每页条数")


class StampingPartCostDeleteDTO(StampingPartCostScopeDTO):
    """批量删除（仅删未审核）。"""


class StampingPartCostBatchApproveDTO(StampingPartCostScopeDTO):
    """批量审核通过。"""

    audit_remark: str | None = Field(None, description="审核意见")


class StampingPartCostBatchReverseAuditDTO(StampingPartCostScopeDTO):
    """批量反审核。"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因")
