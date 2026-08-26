"""成品月核价 DTO。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class L0AssemblyCostCalcDTO(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    location: str = Field(..., min_length=1, max_length=50)
    vehicle_model: str = Field(..., min_length=1, max_length=50)
    bom_version: str = Field(..., min_length=1, max_length=20)


class L0AssemblyCostQuery(BaseModel):
    year: int | None = None
    month: int | None = None
    location: str | None = None
    vehicle_model: str | None = None
    bom_version: str | None = None
    part_number: str | None = None
    audit_status: str | None = None
    calc_status: str | None = None
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=200)


class L0AssemblyCostScopeDTO(BaseModel):
    """批量操作范围（与计算范围一致）。"""

    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    location: str = Field(..., min_length=1, max_length=50)
    vehicle_model: str = Field(..., min_length=1, max_length=50)
    bom_version: str = Field(..., min_length=1, max_length=20)


class L0AssemblyCostBatchApproveDTO(L0AssemblyCostScopeDTO):
    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")


class L0AssemblyCostBatchReverseDTO(L0AssemblyCostScopeDTO):
    reverse_audit_remark: str = Field(..., min_length=1)


class L0AssemblyCostBatchDeleteDTO(L0AssemblyCostScopeDTO):
    """批量删除未审核记录。"""
