"""AnalysisSnapshot：本次分析结果（非万能抽屉）。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.llm.analysis_query import AnalysisQuery

ActionType = Literal["NAVIGATE", "WORKFLOW", "REUSE_EXPLANATION"]


class SnapshotMeta(BaseModel):
    has_data: bool = False
    comparability: Literal["tight", "loose", "unknown"] = "unknown"
    comparison_basis_label: str | None = None
    currency_note: str = "金额单位：元；禁止改写为万元"
    generated_at: str | None = None
    data_message: str | None = None
    unresolved_mentions: list[str] = Field(default_factory=list)


class AnalysisAction(BaseModel):
    action_id: str
    type: ActionType
    label: str
    target: str
    permission: str | None = None
    params: dict[str, str | list[str]] = Field(default_factory=dict)


class AnalysisSnapshot(BaseModel):
    query: AnalysisQuery
    meta: SnapshotMeta
    summary: dict[str, Any] | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    actions: list[AnalysisAction] = Field(default_factory=list)

    def to_prompt_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
