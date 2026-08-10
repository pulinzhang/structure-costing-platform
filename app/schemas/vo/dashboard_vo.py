"""
仪表盘 VO - 响应数据结构
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class CountResponse(BaseModel):
    """计数响应 VO"""
    count: int


class RecentUploadVO(BaseModel):
    """最近上传记录 VO"""
    id: int
    filename: str
    vehicle_model: str
    version: str
    location: str
    uploaded_at: Optional[str] = None


class DashboardStatsVO(BaseModel):
    """仪表盘统计数据 VO"""
    total_parts: int
    total_processes: int
    total_models: int
    recent_uploads: List[RecentUploadVO] = []


class SteelPriceCalcFilterOptionsVO(BaseModel):
    """钢价联动计算页筛选下拉选项"""

    years: list[int] = Field(default_factory=list, description="可选年度")
    months: list[int] = Field(default_factory=list, description="可选月份")
    locations: list[str] = Field(default_factory=list, description="可选基地")


class SteelPriceCalcStatsVO(BaseModel):
    """钢价联动计算 — 数据依据统计 VO"""

    base_price_count: int = Field(..., description="中标基价库条数")
    adjustment_rule_count: int = Field(..., description="厚/宽调价规则条数")
    thickness_row_count: int = Field(..., description="厚度规格行数（冲压材料+厚度去重；基地/工厂/车型全空时为 0）")
    filters: SteelPriceCalcFilterOptionsVO = Field(
        default_factory=SteelPriceCalcFilterOptionsVO,
        description="筛选下拉选项",
    )
