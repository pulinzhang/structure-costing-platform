"""
BOM 焊接费 DTO - 请求参数
"""

from pydantic import BaseModel, Field


class BomL0WeldingFeeScopeDTO(BaseModel):
    """范围必填：年度 + 基地 + 车型 + BOM 版本"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    location: str = Field(..., min_length=1, description="基地")
    vehicle_model: str = Field(..., min_length=1, description="车型")
    bom_version: str = Field(..., min_length=1, description="材料清单版本")


class BomL0WeldingFeeCalcDTO(BomL0WeldingFeeScopeDTO):
    """焊接费计算请求"""


class BomL0WeldingFeeQuery(BaseModel):
    """焊接费列表查询参数"""

    year: int | None = Field(None, description="年度")
    location: str | None = Field(None, description="基地")
    vehicle_model: str | None = Field(None, description="车型")
    bom_version: str | None = Field(None, description="材料清单版本")
    part_number: str | None = Field(None, description="零件号")
    audit_status: str | None = Field(None, description="审核状态")
    calc_status: str | None = Field(None, description="计算状态")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=500, description="每页条数")


class BomL0WeldingFeeBatchApproveDTO(BomL0WeldingFeeScopeDTO):
    """批量审核通过"""

    audit_remark: str | None = Field(None, description="审核意见")


class BomL0WeldingFeeBatchReverseAuditDTO(BomL0WeldingFeeScopeDTO):
    """批量反审核"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")


class BomL0WeldingFeeBatchDeleteDTO(BomL0WeldingFeeScopeDTO):
    """批量删除（仅删未审核；已通过跳过）"""
