"""
BOM 焊接工艺拆解 DTO
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator


class BomWeldingProcessBreakdownGenerateDTO(BaseModel):
    """从 BOM 生成焊接工艺拆解（按基地+项目+版本）"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    vehicle_model: str = Field(..., min_length=1, max_length=50, description="项目/车型")
    bom_version: str = Field(..., min_length=1, max_length=20, description="材料清单版本")
    customer_name: str | None = Field(
        None,
        max_length=100,
        description="顾客名称（可选校验，例：奇瑞公司）",
    )


class BomWeldingProcessBreakdownScopeDTO(BaseModel):
    """范围：基地 + 项目 + 版本"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    vehicle_model: str = Field(..., min_length=1, max_length=50, description="项目/车型")
    bom_version: str = Field(..., min_length=1, max_length=20, description="材料清单版本")


class BomWeldingProcessBreakdownBatchDeleteDTO(BomWeldingProcessBreakdownScopeDTO):
    """批量删除（仅删未审核）"""


class BomWeldingProcessBreakdownBatchApproveDTO(BomWeldingProcessBreakdownScopeDTO):
    """批量审核通过"""

    audit_remark: str | None = Field(None, description="审核意见")


class BomWeldingProcessBreakdownBatchReverseAuditDTO(BomWeldingProcessBreakdownScopeDTO):
    """批量反审核"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")


class BomWeldingProcessBreakdownLineUpdateDTO(BaseModel):
    """修改明细行（单件过程量）；主表须未审核。

    map_status / rollup / qty_check 由 Service 重算，禁止客户端直写。
    """

    process_token: str | None = Field(None, min_length=1, max_length=50)
    process_qty: Decimal | None = Field(None, ge=0)
    process_qty_unit: str | None = Field(None, min_length=1, max_length=20)
    process_qty_secondary: Decimal | None = Field(None, ge=0)
    process_qty_secondary_unit: str | None = Field(None, max_length=20)
    standard_process_name: str | None = Field(
        None, max_length=100, description="标准焊接工艺名称（焊接单价 item_name）"
    )

    @field_validator("process_qty", "process_qty_secondary", mode="before")
    @classmethod
    def _coerce_decimal(cls, value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        return value if isinstance(value, Decimal) else Decimal(str(value).strip())


class BomWeldingProcessBreakdownQuery(BaseModel):
    """分页查询"""

    location: str | None = Field(None, description="采购基地")
    customer_name: str | None = Field(None, description="顾客名称")
    vehicle_model: str | None = Field(None, description="项目/车型")
    bom_version: str | None = Field(None, description="材料清单版本")
    part_number: str | None = Field(None, description="零件号（模糊）")
    level: int | None = Field(None, description="层级 0/1")
    audit_status: str | None = Field(None, description="审核状态")
    parse_status: str | None = Field(None, description="解析状态")
    process_line_count_eq: int | None = Field(
        None,
        description="工艺明细行数精确匹配；传 0 筛无有效工艺（异常）",
    )
    page: int = Field(1, ge=1)
    size: int = Field(50, ge=1, le=500)
