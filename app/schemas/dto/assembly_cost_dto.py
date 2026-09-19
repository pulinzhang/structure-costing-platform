"""总成月核价 DTO。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

AssemblyCostView = Literal["finance", "procurement", "all"]


class AssemblyCostCalcDTO(BaseModel):
    """计算请求：年+月+基地+项目。版本忽略。取该月有效期内 BOM 树。"""

    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    location: str = Field(..., min_length=1, max_length=50)
    vehicle_model: str = Field(..., min_length=1, max_length=50)
    bom_version: str | None = Field(None, description="忽略。取该月有效期内 BOM 树")
    levels: list[int] | None = None

    @field_validator("bom_version", mode="before")
    @classmethod
    def _empty_bom_version_to_none(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class AssemblyCostQuery(BaseModel):
    year: int | None = None
    month: int | None = None
    location: str | None = None
    vehicle_model: str | None = None
    bom_version: str | None = None
    part_number: str | None = None
    audit_status: str | None = None
    calc_status: str | None = None
    view: AssemblyCostView = "finance"
    level: int | None = None
    object_kind: str | None = None
    confirm_status: str | None = None
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=200)


class AssemblyCostScopeDTO(BaseModel):
    """批量操作范围：年+月+基地+项目；版本可选（工程变更后同月可多版本）。"""

    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    location: str = Field(..., min_length=1, max_length=50)
    vehicle_model: str = Field(..., min_length=1, max_length=50)
    bom_version: str | None = Field(
        None,
        max_length=20,
        description="可选。空=该月该项目全部节点版本（含 EC 变更字）",
    )
    view: AssemblyCostView = "finance"

    @field_validator("bom_version", mode="before")
    @classmethod
    def _empty_bom_version_to_none(cls, value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class AssemblyCostBatchApproveDTO(AssemblyCostScopeDTO):
    audit_remark: str = Field(..., min_length=1, description="审核意见（必填）")


class AssemblyCostBatchReverseDTO(AssemblyCostScopeDTO):
    reverse_audit_remark: str = Field(..., min_length=1)


class AssemblyCostBatchDeleteDTO(AssemblyCostScopeDTO):
    """批量删除未审核记录。"""
