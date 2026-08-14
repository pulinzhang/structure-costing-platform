"""
冲压加工费 DTO - 请求参数
"""

from pydantic import BaseModel, Field


class StampingProcessFeeScopeDTO(BaseModel):
    """范围必填：年度 + 基地 + 冲压工厂（计算 / 删除 / 审核 / 反审核共用）"""

    year: int = Field(..., ge=2000, le=2100, description="年度")
    location: str = Field(..., min_length=1, description="基地")
    stamping_supplier: str = Field(..., min_length=1, description="冲压工厂")


class StampingProcessFeeCalcDTO(StampingProcessFeeScopeDTO):
    """冲压加工费计算请求（车型/版本可选，用于缩小计算范围）"""

    vehicle_model: str | None = Field(None, description="车型")
    version: str | None = Field(None, description="版本")


class StampingProcessFeeQuery(BaseModel):
    """冲压加工费列表查询参数"""

    year: int | None = Field(None, description="年度")
    location: str | None = Field(None, description="基地")
    stamping_supplier: str | None = Field(None, description="冲压工厂")
    vehicle_model: str | None = Field(None, description="车型")
    version: str | None = Field(None, description="版本")
    part_number: str | None = Field(None, description="零件号")
    audit_status: str | None = Field(None, description="审核状态")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(20, ge=1, le=500, description="每页条数")


class StampingProcessFeeUpdateDTO(BaseModel):
    """手工调整单价与备注"""

    manual_unit_price: float | None = Field(
        None, ge=0, description="手工调整单价(元)；传 null 表示清空，回退到系统计算值"
    )
    remark: str | None = Field(
        None, max_length=1000, description="备注（调整理由/原因）"
    )


class StampingProcessFeeDeleteDTO(StampingProcessFeeScopeDTO):
    """批量删除（仅删未审核；已通过跳过）"""


class StampingProcessFeeBatchApproveDTO(StampingProcessFeeScopeDTO):
    """批量审核通过"""

    audit_remark: str | None = Field(None, description="审核意见")


class StampingProcessFeeBatchReverseAuditDTO(StampingProcessFeeScopeDTO):
    """批量反审核"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")
