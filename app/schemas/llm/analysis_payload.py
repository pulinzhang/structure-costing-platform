"""LLM 分析 kind payload（TypedDict；金额为 money_str / rate_str 的 str）。

阅读导航（改字段先看这里）：

| 放哪 | 类型 | 说明 |
|------|------|------|
| `snapshot.summary` | `AnalysisSummaryBag` | KPI 袋或引擎门禁摘要；**无** `kind` 信封（engine 例外） |
| `snapshot.result` | `AnalysisResultPayload` | 带 `kind` 的分析结果；多段时为 `composite` |
| `snapshot.evidence` | `EvidencePayload` | 给模型的旁证，键按需扩展 |

`AnalysisKind`（query）核心六种：`summary`/`trend`/`drivers`/`comparison`/`risk`/`drilldown`。
域扩展 kind（`mom_anomalies`、`policy_anomalies`、`part_existence` 等）也挂在
`AnalysisResultLeafPayload` 上，避免 compose 退回裸 dict。

金额/比率在 payload 里一律是格式化后的 **str**（见 `_money.money_str` /
`rate_str`），不要改回 Decimal。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, NotRequired, TypeAlias

from typing_extensions import TypedDict

# ---------------------------------------------------------------------------
# 开放袋（域 KPI / 旁证键多变；具名 TypeAlias，禁止 Any）
# ---------------------------------------------------------------------------

SummaryPayload: TypeAlias = dict[str, object]  # noqa: UP040
EvidencePayload: TypeAlias = dict[str, object]  # noqa: UP040
# comparison / drilldown / 动因行：域扩展键多，具名开放袋（禁止 Any）
ComparisonPayload: TypeAlias = dict[str, object]  # noqa: UP040
DrilldownPayload: TypeAlias = dict[str, object]  # noqa: UP040
DriverItem: TypeAlias = dict[str, object]  # noqa: UP040


# ---------------------------------------------------------------------------
# summary 月份行等仍保留 TypedDict，供文档与局部注解
# ---------------------------------------------------------------------------


class SummaryMonthRow(TypedDict, total=False):
    month: str
    location: str
    grand_total_sum: str
    l0_count: int
    part_count: int
    unit_cost_sum: str
    success_count: int
    avg_final_price: str
    row_count: int
    ladder_row_count: int


class SummaryBreakdown(TypedDict, total=False):
    stamping_amount_sum: str
    purchased_amount_sum: str
    bundle_amount_sum: str
    welding_amount_sum: str
    welding_other_amount_sum: str


# ---------------------------------------------------------------------------
# trend
# ---------------------------------------------------------------------------


class _TrendPointRequired(TypedDict):
    month: str


class TrendPoint(_TrendPointRequired, total=False):
    """价值列键随 value_label 变化（grand_total_sum / avg_final_price / …）。"""

    mom_delta: str | None
    mom_rate: str | None
    grand_total_sum: str
    avg_final_price: str
    unit_cost_sum: str
    non_zero_ladder_count: str


class TrendPayload(TypedDict, total=False):
    kind: Literal["trend"]
    points: list[TrendPoint]
    comparability: str
    comparison_basis_label: str
    anomaly_months: list[str]
    anomaly_note: str | None
    min: str
    max: str
    avg: str
    start: str
    end: str
    cumulative_delta: str
    cumulative_rate: str | None
    notes: str | None
    subject: str


# ---------------------------------------------------------------------------
# drivers
# ---------------------------------------------------------------------------


class DriversPayload(TypedDict):
    kind: Literal["drivers"]
    top_n: int
    items: NotRequired[list[DriverItem]]
    top_items: NotRequired[list[DriverItem]]
    up_contribution: NotRequired[list[DriverItem]]
    down_drag: NotRequired[list[DriverItem]]
    concentration: NotRequired[str]
    top_cumulative_contribution: NotRequired[str]


# ---------------------------------------------------------------------------
# comparison（形状文档；运行时 ComparisonPayload 为开放袋）
# ---------------------------------------------------------------------------


class ComparisonPoint(TypedDict, total=False):
    month: str
    grand_total_sum: str
    value: str


class ComparisonSeriesItem(TypedDict, total=False):
    location: str
    points: list[ComparisonPoint]
    start: str
    end: str
    change: str
    change_rate: str | None
    status: str
    label: str


class SpreadResult(TypedDict):
    spread: str | None
    status: str


class ComparisonSpread(TypedDict, total=False):
    location_a: str
    location_b: str
    spread: str | None
    status: str
    label_a: str
    label_b: str


class ComparisonWinner(TypedDict, total=False):
    location: str
    by: str
    label: str


# ---------------------------------------------------------------------------
# risk
# ---------------------------------------------------------------------------


class RiskSampleRow(TypedDict, total=False):
    """风险抽样行：字段随 risk_type 变化。"""

    part_number: str
    part_name: str | None
    month: str
    year: int
    unit_price: str
    unit_cost: str
    should_cost: str | None
    total_amount: str
    grand_total: str
    calc_status: str
    calc_message: str | None
    missing_leaf_count: int
    stamping_supplier: str | None
    vehicle_model: str | None


class RiskEntry(TypedDict, total=False):
    risk_type: str
    severity: str
    count: int
    message: str
    sample_part_numbers: Sequence[object]
    reason_counts: dict[str, int]
    status_counts: dict[str, int]
    samples: Sequence[object]
    zero_unit_price_items: Sequence[object]
    missing_price_items: Sequence[object]
    missing_supplier_items: Sequence[object]
    composition_items: Sequence[object]
    standard_part_items: Sequence[object]
    conversion_items: Sequence[object]
    truncated: bool


class RiskPayload(TypedDict, total=False):
    kind: Literal["risk"]
    risks: list[RiskEntry]
    partial_count: int
    missing_price_count: int
    zero_unit_price_count: int
    filtered_missing_price_count: int
    composition_dominance_count: int
    standard_part_high_price_count: int
    annual_price_conversion_count: int
    pending_audit_count: int
    incomplete_count: int
    pending_confirm_count: int


# ---------------------------------------------------------------------------
# drilldown（形状文档；运行时 DrilldownPayload 为开放袋）
# ---------------------------------------------------------------------------


class PeriodDiffComponent(TypedDict):
    cost_component: str
    label: str
    start: str
    end: str
    delta: str
    share: str | None


class PeriodDiffPayload(TypedDict):
    start_month: str
    end_month: str
    start_value: str
    end_value: str
    delta: str
    delta_rate: str | None
    components: list[PeriodDiffComponent]


class DrilldownLatest(TypedDict, total=False):
    month: str
    year: int
    month_number: int
    grand_total: str
    total_amount: str
    stamping_amount: str
    purchased_amount: str
    bundle_amount: str
    welding_amount: str
    welding_other_fee: str
    indirect_amount: str
    calc_status: str
    calc_message: str | None
    missing_leaf_count: int
    bom_version: str | None
    location: str | None
    unit_price: str
    line_amount: str
    cost_source: str
    supply_type: str
    vehicle_model: str | None
    card_role: str
    level: int
    is_tree_root: bool
    object_kind: str | None
    root_part_number: str | None


class DrilldownPoint(TypedDict, total=False):
    month: str
    grand_total: str
    total_amount: str
    calc_status: str
    bom_version: str | None
    card_role: str


class KindOnlyPayload(TypedDict):
    """compose 在 analyses 为空时返回的最小信封。"""

    kind: str


class EmptyResultPayload(TypedDict, total=False):
    """RunResult / Snapshot 构造前的空 result。"""

    kind: str


class MomAnomalyItem(TypedDict, total=False):
    anomaly_type: str
    part_number: str
    part_name: str | None
    month: str
    prev_month: str | None
    prev_cost: str | None
    curr_cost: str | None
    change: str | int | None
    change_rate: str | None
    calc_status: str
    stamping_supplier: str | None
    vehicle_model: str | None
    threshold: str
    period_grain: str
    rank: int
    missing_leaf_count: int
    calc_message: str
    location: str
    steel_mill: str
    category_name: str
    policy_type: str
    grade: str
    grade_value: str | None
    spec: str
    thickness_band: str
    prev_adjustment: str | int
    curr_adjustment: str | int
    prev_sheet_name: str
    sheet_name: str
    prev_base_price: str
    curr_base_price: str
    hint: str


class MomAnomaliesPayload(TypedDict, total=False):
    kind: Literal["mom_anomalies"]
    items: list[MomAnomalyItem]
    top_n: int
    subject: str


class CompositionAnomalyItem(TypedDict, total=False):
    anomaly_type: str
    month: str
    root_part_number: str
    root_part_name: str | None
    root_should_cost: str
    child_part_number: str
    child_part_name: str | None
    cost_source: str
    cost_source_label: str
    unit_price: str
    effective_qty: str
    line_amount: str
    share_of_should_cost: str


class CompositionAnomaliesPayload(TypedDict):
    kind: Literal["composition_anomalies"]
    threshold: str
    extreme_qty_threshold: str
    items: list[CompositionAnomalyItem]


class DomainAnomaliesPayload(TypedDict, total=False):
    """policy / base_price / annual_price / standard_part 等域异常列表。"""

    kind: Literal[
        "policy_anomalies",
        "base_price_anomalies",
        "base_price_month_move_over",
        "annual_price_anomalies",
        "standard_part_anomalies",
    ]
    items: Sequence[object]
    top_n: int
    count: int
    note: str
    lines: list[str]
    table: str
    threshold: str
    conversion_factor_min: str
    subject: str


class PartPresenceBlock(TypedDict, total=False):
    found: bool
    source: str
    applicable: bool
    expected_absence: bool
    message: str
    note: str
    row_count: int
    part_number: str
    part_name: str | None
    card_role: str
    is_tree_root: bool
    level: int
    object_kind: str | None
    root_part_number: str | None
    latest_month: str
    grand_total: str
    total_amount: str
    calc_status: str
    bom_version: str | None
    identity_count: int
    identities: list[dict[str, object]]
    unit_cost: str
    stamping_supplier: str | None
    material: str | None
    thickness: str | None
    location: str | None
    vehicle_model: str | None
    version: str | None
    process_count: int


class PartExistencePayload(TypedDict, total=False):
    kind: Literal["part_existence"]
    query_token: str
    primary_source: str | None
    domain_note: str | None
    exists_any: bool
    l0: PartPresenceBlock
    stamping_cost: PartPresenceBlock
    stamping_process: PartPresenceBlock


class OpsWorkbenchPayload(TypedDict):
    kind: Literal["ops_workbench"]
    items: NotRequired[list[dict[str, object]]]
    message: NotRequired[str]
    boards: NotRequired[list[dict[str, object]]]
    board_count: NotRequired[int]
    open_issue_count: NotRequired[int]
    subject: NotRequired[str]
    pending_audit_total: NotRequired[int]
    incomplete_total: NotRequired[int]
    pending_confirm_total: NotRequired[int]
    empty_board_labels: NotRequired[list[str]]
    has_attention: NotRequired[bool]


class EngineReadinessGate(TypedDict, total=False):
    code: str
    label: str
    ok: bool
    hard_stop: bool
    soft_hint: bool
    message: str
    missing: list[str]
    navigate_page: str | None
    navigate_label: str | None


class EngineReadinessPayload(TypedDict, total=False):
    kind: Literal["engine_readiness"]
    location: str | None
    year: int | None
    month: int | None
    can_start: bool
    hard_stop: bool
    hard_fail_count: int
    soft_hint_count: int
    ok_count: int
    ready_count: int
    gates: list[EngineReadinessGate]
    l0_scopes: list[str]
    vehicle_models: list[str]
    message: str
    plan: NotRequired[dict[str, object]]
    evidence_note: NotRequired[str]


# summary 槽：成品 KPI、引擎门禁或运维工作台摘要
AnalysisSummaryBag = SummaryPayload | EngineReadinessPayload | OpsWorkbenchPayload


# 叶子 result（不含 composite；summary 袋可进 parts_result）
AnalysisResultLeafPayload = (
    SummaryPayload
    | TrendPayload
    | DriversPayload
    | ComparisonPayload
    | RiskPayload
    | DrilldownPayload
    | MomAnomaliesPayload
    | CompositionAnomaliesPayload
    | DomainAnomaliesPayload
    | PartExistencePayload
    | OpsWorkbenchPayload
    | EngineReadinessPayload
    | KindOnlyPayload
    | EmptyResultPayload
)


class CompositePayload(TypedDict):
    kind: Literal["composite"]
    parts: dict[str, AnalysisResultLeafPayload]


AnalysisResultPayload = AnalysisResultLeafPayload | CompositePayload
