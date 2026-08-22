"""LLM 分析报告请求 DTO — 仅自然语言。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class LlmAnalysisReportCreateDTO(BaseModel):
    """POST /api/llm/reports — 只需自然语言问题。"""

    user_question: str = Field(..., min_length=1, max_length=2000)
    audience: str | None = Field(None, max_length=40)
    idempotency_key: str | None = Field(None, max_length=200)
    force_refresh: bool = False

    @field_validator("user_question", "audience", "idempotency_key", mode="before")
    @classmethod
    def _strip_text(cls, value: object) -> object:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class LlmAnalysisReportQuery(BaseModel):
    location: str | None = None
    year: int | None = None
    month: int | None = None
    vehicle_model: str | None = None
    bom_version: str | None = None
    report_type: str | None = None
    status: str | None = None
    skip: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)
