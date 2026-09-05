"""
仪表盘 VO - 管理者看板响应结构
"""

from decimal import Decimal

from pydantic import BaseModel, Field, field_serializer

from app.common.money import Q2, Q3, Q4, Q6, optional_format_money


class DashboardScopeVO(BaseModel):
    """看板作用域：当期年 / 月 / 基地 / 车型 + 下拉选项"""

    year: int
    month: int
    location: str | None = None
    vehicle_model: str | None = None
    years: list[int] = Field(default_factory=list, description="可选年度")
    months: list[int] = Field(default_factory=list, description="可选月份")
    locations: list[str] = Field(default_factory=list, description="可选生产基地")
    vehicle_models: list[str] = Field(default_factory=list, description="可选配套车型")


class DashboardMasterStatsVO(BaseModel):
    """主数据底盘（全库，不受月度限制）"""

    parts: int = 0
    processes: int = 0
    models: int = 0


class DashboardYishiyiyiStatsVO(BaseModel):
    """一事一议当期依据（基价随基地；选车型时按该车牌号覆盖；政策为当期全国或按车型分类）"""

    base_price_count: int = 0
    policy_count: int = 0
    scrap_filled_count: int = 0
    scrap_required_count: int = 0
    is_scrap_complete: bool = False
    scrap_location: str | None = None
    is_scrap_location_filled: bool | None = None
    scrap_location_net_price: Decimal | None = None

    @field_serializer("scrap_location_net_price")
    def serialize_net_price(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q2, 2)


class DashboardAuditBucketVO(BaseModel):
    """审核态桶：加工费 / 钢价 / 冲压零件价"""

    pending_count: int = 0
    approved_count: int = 0
    zero_count: int | None = None
    total_count: int | None = None
    avg_value: Decimal | None = None

    @field_serializer("avg_value")
    def serialize_avg_value(self, value: Decimal | None) -> str | None:
        # 桶内均价可能是加工费(Q3) / 钢价(Q4) / 零件价(Q6)，统一按较高精度输出
        return optional_format_money(value, Q6, 6)


class DashboardBomStatsVO(BaseModel):
    """BOM 覆盖"""

    snapshot_count: int = 0
    node_count: int = 0


class DashboardReadinessVO(BaseModel):
    """当期核价闭环就绪（管理者解读）"""

    has_base_price: bool = False
    has_policy: bool = False
    is_scrap_complete: bool = False
    has_process_fee: bool = False
    has_steel_price: bool = False
    has_part_cost: bool = False
    ready_count: int = 0
    total_count: int = 6


class DashboardAttentionItemVO(BaseModel):
    """待办 / 风险项（可跳转处理）"""

    code: str
    severity: str = Field(..., description="critical | warning | info")
    title: str
    detail: str
    count: int | None = None
    page: str | None = Field(None, description="前端 hash 页名，如 stamping-part-cost")


class DashboardOutcomeVO(BaseModel):
    """本期经营结果摘要"""

    pending_total: int = 0
    process_fee_pending: int = 0
    steel_price_pending: int = 0
    part_cost_pending: int = 0
    process_fee_zero: int = 0
    part_cost_approved: int = 0
    part_cost_avg: Decimal | None = None
    steel_price_avg: Decimal | None = None
    process_fee_avg: Decimal | None = None

    @field_serializer("part_cost_avg")
    def serialize_part_cost_avg(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q6, 6)

    @field_serializer("steel_price_avg")
    def serialize_steel_price_avg(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q4, 4)

    @field_serializer("process_fee_avg")
    def serialize_process_fee_avg(self, value: Decimal | None) -> str | None:
        return optional_format_money(value, Q3, 3)


class DashboardStatsVO(BaseModel):
    """管理者看板：作用域 + 产出 + 待办 + 就绪 + 明细桶"""

    scope: DashboardScopeVO
    outcome: DashboardOutcomeVO
    readiness: DashboardReadinessVO
    attention: list[DashboardAttentionItemVO] = Field(default_factory=list)
    master: DashboardMasterStatsVO
    yishiyiyi: DashboardYishiyiyiStatsVO
    process_fee: DashboardAuditBucketVO
    steel_price: DashboardAuditBucketVO
    part_cost: DashboardAuditBucketVO
    bom: DashboardBomStatsVO


class SteelPriceCalcFilterOptionsVO(BaseModel):
    """钢价联动计算页筛选下拉选项"""

    years: list[int] = Field(default_factory=list, description="可选年度")
    months: list[int] = Field(default_factory=list, description="可选月份")
    locations: list[str] = Field(default_factory=list, description="可选基地")
    vehicle_models: list[str] = Field(default_factory=list, description="可选配套车型")


class SteelPriceCalcStatsVO(BaseModel):
    """钢价联动计算 — 数据依据统计 VO"""

    base_price_count: int = Field(..., description="中标基价库条数")
    adjustment_rule_count: int = Field(..., description="厚/宽调价规则条数")
    thickness_row_count: int = Field(
        ...,
        description="厚度规格行数（冲压材料+厚度去重；未选基地时为 0；可选车型收窄）",
    )
    filters: SteelPriceCalcFilterOptionsVO = Field(
        default_factory=SteelPriceCalcFilterOptionsVO,
        description="筛选下拉选项",
    )
