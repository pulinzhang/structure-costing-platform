"""
焊接工费单价 DTO - 内部传输/请求参数
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from app.common.bom.welding_standard_process import validate_welding_unit_price_catalog
from app.common.money import Q4, quantize_money
from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
)


def quantize_unit_price(value: object) -> Decimal:
    """解析并量化为 4 位小数 Decimal（禁止以 float 作为业务类型）。"""
    return quantize_money(value, Q4)


class BomWeldingUnitPriceCreate(BaseModel):
    """焊接工费单价创建请求"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    year: int = Field(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="年份")
    item_name: str = Field(..., min_length=1, max_length=100, description="操作项目名称")
    unit: str = Field(..., min_length=1, max_length=20, description="计量单位")
    unit_price: Decimal = Field(..., ge=0, description="工费单价(元/单位)，Decimal 保留4位小数")
    remark: str | None = Field(None, description="备注")

    @field_validator("unit_price", mode="before")
    @classmethod
    def _coerce_unit_price(cls, value: object) -> Decimal:
        return quantize_unit_price(value)

    @field_validator("item_name", mode="before")
    @classmethod
    def _strip_item_name(cls, value: object) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @model_validator(mode="after")
    def _validate_standard_catalog(self) -> "BomWeldingUnitPriceCreate":
        validate_welding_unit_price_catalog(self.item_name, self.unit)
        return self


class BomWeldingUnitPriceUpdate(BaseModel):
    """焊接工费单价更新请求"""

    unit: str | None = Field(None, min_length=1, max_length=20, description="计量单位")
    unit_price: Decimal = Field(..., ge=0, description="工费单价(元/单位)，Decimal 保留4位小数")
    remark: str | None = Field(None, description="备注")

    @field_validator("unit_price", mode="before")
    @classmethod
    def _coerce_unit_price(cls, value: object) -> Decimal:
        return quantize_unit_price(value)


class BomWeldingUnitPriceQuery(BaseModel):
    """焊接工费单价查询参数"""

    location: str | None = Field(None, description="采购基地")
    year: int | None = Field(None, description="年份")
    audit_status: str | None = Field(None, description="审核状态")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=500, description="每页条数")


class BomWeldingUnitPriceScopeDTO(BaseModel):
    """范围必填：基地 + 年度（上传 / 删除 / 审核 / 反审核共用）"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地（必填）")
    year: int = Field(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="年度（必填）")


class BomWeldingUnitPriceBatchDeleteDTO(BomWeldingUnitPriceScopeDTO):
    """按基地 + 年度批量删除（仅删未审核；已通过跳过）"""


class BomWeldingUnitPriceBatchApproveDTO(BomWeldingUnitPriceScopeDTO):
    """批量审核通过"""

    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")


class BomWeldingUnitPriceBatchReverseAuditDTO(BomWeldingUnitPriceScopeDTO):
    """批量反审核"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因（必填）")
