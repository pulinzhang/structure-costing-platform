"""AnalysisQuery：Scope（filters+time+basis）+ Intent（analyses）。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

AnalysisKind = Literal[
    "summary",
    "trend",
    "drivers",
    "comparison",
    "risk",
    "drilldown",
]

QueryMode = Literal["analysis", "usage_help"]


class TimeRange(BaseModel):
    """YYYY-MM 闭区间。"""

    start: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    end: str = Field(..., pattern=r"^\d{4}-\d{2}$")

    @property
    def start_year(self) -> int:
        return int(self.start[:4])

    @property
    def start_month(self) -> int:
        return int(self.start[5:7])

    @property
    def end_year(self) -> int:
        return int(self.end[:4])

    @property
    def end_month(self) -> int:
        return int(self.end[5:7])

    def month_span(self) -> int:
        return (
            self.end_year * 12
            + self.end_month
            - (self.start_year * 12 + self.start_month)
            + 1
        )


class ComparisonBasis(BaseModel):
    same_part: bool = True
    same_bom_version: bool = True
    same_material: bool = False
    same_process: bool = False
    same_formula_version: bool = False
    label: str = "same_part_and_bom"
    notes: str | None = None


class AnalysisQuery(BaseModel):
    """一次分析的结构化查询。"""

    time_range: TimeRange
    filters: dict[str, str] = Field(default_factory=dict)
    subject: str = "cost_total"
    comparison_basis: ComparisonBasis = Field(default_factory=ComparisonBasis)
    analyses: list[AnalysisKind] = Field(default_factory=lambda: ["summary"])
    user_question: str = ""
    unresolved_mentions: list[str] = Field(default_factory=list)
    query_mode: QueryMode = "analysis"
    help_topic: str | None = None

    @field_validator("filters", mode="before")
    @classmethod
    def _normalize_filters(cls, value: object) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        out: dict[str, str] = {}
        for key, raw in value.items():
            if raw is None:
                continue
            text = str(raw).strip()
            if text:
                out[str(key).strip()] = text
        return out

    @field_validator("analyses", mode="before")
    @classmethod
    def _dedupe_analyses(cls, value: object) -> list[str]:
        if not value:
            return ["summary"]
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple)):
            return ["summary"]
        allowed = {
            "summary",
            "trend",
            "drivers",
            "comparison",
            "risk",
            "drilldown",
        }
        seen: list[str] = []
        for item in value:
            kind = str(item).strip().lower()
            if kind in allowed and kind not in seen:
                seen.append(kind)
        return seen or ["summary"]

    def filter_get(self, key: str, default: str | None = None) -> str | None:
        return self.filters.get(key, default)

    def location(self) -> str | None:
        return self.filter_get("location")

    def vehicle_model(self) -> str | None:
        return self.filter_get("vehicle_model")

    def bom_version(self) -> str | None:
        return self.filter_get("bom_version")

    def part_number(self) -> str | None:
        return self.filter_get("part_number")

    def tonnage(self) -> int | None:
        raw = self.filter_get("tonnage")
        if raw is None:
            return None
        text = raw.strip()
        if text.isdigit():
            return int(text)
        return None

    def analyses_key(self) -> str:
        if self.query_mode == "usage_help":
            return "usage_help"
        return ",".join(self.analyses)
