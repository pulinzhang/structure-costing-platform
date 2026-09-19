"""Repository 聚合与 JSON 列载荷：固定键用 TypedDict，禁止签名写匿名 dict。"""

from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict


class AsyncTaskSnapshot(TypedDict):
    """辅助库异步任务轮询快照。"""

    task_id: str
    task_type: str
    status: str
    progress: int
    message: str
    result_json: str | None
    operator_id: int | None
    operator_name: str | None
    updated_at: datetime | None


class StampingPartFilterSummary(TypedDict):
    """冲压零件列表按筛选汇总。"""

    location_count: int
    stamping_supplier_count: int
    vehicle_model_count: int
    part_number_count: int
    version_count: int


class StampingPartCascadeFilterOptions(TypedDict):
    """冲压零件级联筛选项。"""

    locations: list[str]
    stamping_suppliers: list[str]
    vehicle_models: list[str]
    versions: list[str]


class BomCascadeFilterOptions(TypedDict):
    """材料清单级联筛选项。"""

    locations: list[str]
    vehicle_models: list[str]
    bom_versions: list[str]


class OperationLogCatalogOption(TypedDict):
    """操作日志权限目录筛选项。"""

    code: str
    label: str
    parent_code: str | None
    breadcrumb: str


class OperationLogFilterOptions(TypedDict):
    """操作日志筛选项（权限目录）。"""

    menus: list[OperationLogCatalogOption]
    operations: list[OperationLogCatalogOption]


class ScrapPriceFilterOptions(TypedDict):
    """废料价筛选项（仅已有数据的年份）。"""

    years: list[int]


class SteelBasePriceFilterOptions(TypedDict):
    """钢材基准价筛选项。"""

    years: list[int]
    months: list[int]
    locations: list[str]
    steel_mills: list[str]
    category_names: list[str]
    grades: list[str]
    specs: list[str]


class FileTraceFilterValues(TypedDict):
    """文件溯源筛选项。"""

    categories: list[str]
    locations: list[str]
    years: list[int]
    months: list[int]
    vehicle_models: list[str]
    creators: list[str]


class EngineNavigateJson(TypedDict, total=False):
    page: str
    label: str
    query: dict[str, str | int]
    secondary_page: str | None
    secondary_label: str | None


class EngineGateItemJson(TypedDict, total=False):
    code: str
    ok: bool
    missing: list[str]
    message: str
    navigate: EngineNavigateJson


class EngineAnnualItemJson(TypedDict, total=False):
    code: str
    scope_key: str
    exists: bool
    will_auto_calc: bool


class GateJson(TypedDict, total=False):
    """costing_engine_run.gate_json。"""

    hard_stop: bool
    upload_or_config: list[EngineGateItemJson]
    annual_derived: list[EngineAnnualItemJson]


class EnginePartCostScopeJson(TypedDict):
    vehicle_model: str


class EngineL0ScopeJson(TypedDict):
    vehicle_model: str
    bom_version: str


class PlanJson(TypedDict, total=False):
    """costing_engine_run.plan_json。"""

    steel: dict[str, object]
    part_cost_scopes: list[EnginePartCostScopeJson]
    l0_scopes: list[EngineL0ScopeJson]


class EngineStepSummaryJson(TypedDict, total=False):
    stage: str
    scope_key: str
    status: str
    message: str | None


class EngineCountsJson(TypedDict, total=False):
    succeeded: int
    failed: int
    skipped: int


class SummaryJson(TypedDict, total=False):
    """costing_engine_run.summary_json。"""

    status: str
    location: str
    year: int
    month: int
    steps: list[EngineStepSummaryJson]
    counts: EngineCountsJson
    error: NotRequired[str]


class StepMetricsJson(TypedDict, total=False):
    """costing_engine_run_step.metrics_json。"""

    status: str
    result: bool
    created_count: int | None
    updated_count: int | None
    object_count: int
    node_count: int
    line_count: int


class EngineWorkerResultJson(SummaryJson, total=False):
    """引擎 worker 写入异步任务 result 的载荷（summary + run_id）。"""

    run_id: int
    started_at: str
    finished_at: str
    duration_seconds: int
