"""核价引擎响应 VO。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.common.timezone import datetime_to_iso


class CostingEngineNavigateVO(BaseModel):
    """硬停项功能页深链。"""

    page: str
    label: str
    query: dict[str, str | int] = Field(default_factory=dict)
    secondary_page: str | None = None
    secondary_label: str | None = None


class CostingEngineGateItemVO(BaseModel):
    """上传/配置门禁项。"""

    code: str
    ok: bool
    missing: list[str] = Field(default_factory=list)
    message: str = ""
    navigate: CostingEngineNavigateVO | None = None


class CostingEngineAnnualItemVO(BaseModel):
    """年度计算所得体检项。"""

    code: str
    scope_key: str
    exists: bool
    will_auto_calc: bool


class CostingEnginePartCostScopeVO(BaseModel):
    vehicle_model: str


class CostingEngineL0ScopeVO(BaseModel):
    vehicle_model: str
    bom_version: str


class CostingEnginePlanVO(BaseModel):
    steel: dict[str, Any] = Field(default_factory=dict)
    part_cost_scopes: list[CostingEnginePartCostScopeVO] = Field(default_factory=list)
    l0_scopes: list[CostingEngineL0ScopeVO] = Field(default_factory=list)


class CostingEngineGatesVO(BaseModel):
    hard_stop: bool
    upload_or_config: list[CostingEngineGateItemVO] = Field(default_factory=list)
    annual_derived: list[CostingEngineAnnualItemVO] = Field(default_factory=list)


class CostingEngineReadyVO(BaseModel):
    """GET /ready 契约。"""

    input: dict[str, Any]
    gates: CostingEngineGatesVO
    plan: CostingEnginePlanVO
    can_start: bool


class CostingEngineRunStepVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: str
    scope_key: str
    status: str
    child_task_id: str | None = None
    child_log_id: int | None = None
    message: str | None = None
    metrics_json: dict[str, Any] | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_serializer("started_at", "finished_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


class CostingEngineRunVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    location: str
    year: int
    month: int
    status: str
    task_id: str | None = None
    gate_json: dict[str, Any] | None = None
    plan_json: dict[str, Any] | None = None
    summary_json: dict[str, Any] | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    steps: list[CostingEngineRunStepVO] = Field(default_factory=list)

    @field_serializer("created_at", "started_at", "finished_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)


class CostingEngineRunListItemVO(BaseModel):
    """历史列表精简项。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    location: str
    year: int
    month: int
    status: str
    task_id: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_serializer("created_at", "started_at", "finished_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return datetime_to_iso(value)
