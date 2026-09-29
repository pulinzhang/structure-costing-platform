"""
BOM 包装运输费 DTO
"""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.common.money import Q4, quantize_money
from app.common.period import (
    COSTING_YEAR_MAX,
    COSTING_YEAR_MIN,
)


def quantize_fee(value: Any) -> Decimal:
    """解析并量化为 4 位小数 Decimal。"""
    return quantize_money(value, Q4)


class BomPackagingTransportFeeCreate(BaseModel):
    """包装运输费创建请求"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    year: int = Field(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="定价年度")
    vehicle_model: str = Field(..., min_length=1, max_length=50, description="项目")
    part_number: str = Field(..., min_length=1, max_length=50, description="零件号")
    part_name: str | None = Field(None, max_length=200, description="产品名称")
    packaging_type: str | None = Field(None, max_length=50, description="包装类型")
    pieces_per_pack: int | None = Field(None, ge=0, description="单包装数")
    fixture_length_mm: int | None = Field(None, ge=0, description="器具长(mm)")
    fixture_width_mm: int | None = Field(None, ge=0, description="器具宽(mm)")
    fixture_height_mm: int | None = Field(None, ge=0, description="器具高(mm)")
    oem_stock_qty: int | None = Field(None, ge=0, description="上线及主机厂库存数量")
    transit_qty: int | None = Field(None, ge=0, description="在途及返还周转数量")
    company_stock_qty: int | None = Field(None, ge=0, description="公司库存周转数量")
    total_fixture_qty: int | None = Field(None, ge=0, description="器具总投入数量")
    fixture_unit_price: Decimal | None = Field(None, ge=0, description="器具单价")
    fixture_invest_amount: Decimal | None = Field(None, ge=0, description="器具投入总金额")
    unit_packaging_fee: Decimal = Field(..., ge=0, description="单件包装费")
    round_trip_transport_price: Decimal | None = Field(None, ge=0, description="往返运输价格")
    unit_transport_fee: Decimal = Field(..., ge=0, description="单件运输费")
    fixture_maint_fee: Decimal = Field(..., ge=0, description="器具年损维护费")
    other_fee: Decimal = Field(Decimal("0"), ge=0, description="其它费用合计")
    packaging_transport_total: Decimal = Field(..., ge=0, description="包装运输费合计")
    remark: str | None = Field(None, description="备注")
    excel_filename: str | None = Field(None, max_length=255, description="来源 Excel 文件名")
    sheet_name: str | None = Field(None, max_length=100, description="来源工作表名")
    excel_row: int | None = Field(None, ge=1, description="来源 Excel 行号")

    @field_validator(
        "fixture_unit_price",
        "fixture_invest_amount",
        "round_trip_transport_price",
        mode="before",
    )
    @classmethod
    def _coerce_optional_money(cls, value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        return quantize_fee(value)

    @field_validator(
        "unit_packaging_fee",
        "unit_transport_fee",
        "fixture_maint_fee",
        "other_fee",
        "packaging_transport_total",
        mode="before",
    )
    @classmethod
    def _coerce_required_money(cls, value: Any) -> Decimal:
        if value is None or value == "":
            return quantize_fee(Decimal("0"))
        return quantize_fee(value)


class BomPackagingTransportFeeUpdate(BaseModel):
    """包装运输费更新请求（exclude_unset 写入）"""

    part_name: str | None = Field(None, max_length=200)
    packaging_type: str | None = Field(None, max_length=50)
    pieces_per_pack: int | None = Field(None, ge=0)
    fixture_length_mm: int | None = Field(None, ge=0)
    fixture_width_mm: int | None = Field(None, ge=0)
    fixture_height_mm: int | None = Field(None, ge=0)
    oem_stock_qty: int | None = Field(None, ge=0)
    transit_qty: int | None = Field(None, ge=0)
    company_stock_qty: int | None = Field(None, ge=0)
    total_fixture_qty: int | None = Field(None, ge=0)
    fixture_unit_price: Decimal | None = Field(None, ge=0)
    fixture_invest_amount: Decimal | None = Field(None, ge=0)
    unit_packaging_fee: Decimal = Field(..., ge=0)
    round_trip_transport_price: Decimal | None = Field(None, ge=0)
    unit_transport_fee: Decimal = Field(..., ge=0)
    fixture_maint_fee: Decimal = Field(..., ge=0)
    other_fee: Decimal = Field(..., ge=0)
    packaging_transport_total: Decimal = Field(..., ge=0)
    remark: str | None = Field(None)
    excel_filename: str | None = Field(None, max_length=255)
    sheet_name: str | None = Field(None, max_length=100)
    excel_row: int | None = Field(None, ge=1)

    @field_validator(
        "fixture_unit_price",
        "fixture_invest_amount",
        "round_trip_transport_price",
        mode="before",
    )
    @classmethod
    def _coerce_optional_money(cls, value: Any) -> Decimal | None:
        if value is None or value == "":
            return None
        return quantize_fee(value)

    @field_validator(
        "unit_packaging_fee",
        "unit_transport_fee",
        "fixture_maint_fee",
        "other_fee",
        "packaging_transport_total",
        mode="before",
    )
    @classmethod
    def _coerce_required_money(cls, value: Any) -> Decimal:
        if value is None or value == "":
            return quantize_fee(Decimal("0"))
        return quantize_fee(value)


class BomPackagingTransportFeeQuery(BaseModel):
    """包装运输费查询参数"""

    location: str | None = Field(None, description="采购基地")
    year: int | None = Field(None, description="定价年度")
    vehicle_model: str | None = Field(None, description="项目")
    audit_status: str | None = Field(None, description="审核状态")
    keyword: str | None = Field(None, max_length=100, description="零件号或名称模糊搜索")
    page: int = Field(1, ge=1, description="页码")
    size: int = Field(100, ge=1, le=500, description="每页条数")


class BomPackagingTransportFeeScopeDTO(BaseModel):
    """范围：基地 + 年度 + 项目"""

    location: str = Field(..., min_length=1, max_length=50, description="采购基地")
    year: int = Field(..., ge=COSTING_YEAR_MIN, le=COSTING_YEAR_MAX, description="年度")
    vehicle_model: str = Field(..., min_length=1, max_length=50, description="项目")


class BomPackagingTransportFeeBatchDeleteDTO(BomPackagingTransportFeeScopeDTO):
    """按范围批量删除（仅删未审核）"""


class BomPackagingTransportFeeBatchApproveDTO(BomPackagingTransportFeeScopeDTO):
    """批量审核通过"""

    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")


class BomPackagingTransportFeeBatchReverseAuditDTO(BomPackagingTransportFeeScopeDTO):
    """批量反审核"""

    reverse_audit_remark: str = Field(..., min_length=1, description="反审核原因")
