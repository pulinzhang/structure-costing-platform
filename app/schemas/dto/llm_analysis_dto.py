"""LLM 分析报告请求 DTO — 仅自然语言。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class LlmAnalysisReportCreateDTO(BaseModel):
    """POST /api/llm/reports — 自然语言问题；可选上一份报告 id 沿用范围。"""

    user_question: str = Field(..., min_length=1, max_length=2000)
    audience: str | None = Field(None, max_length=40)
    idempotency_key: str | None = Field(None, max_length=200)
    force_refresh: bool = False
    previous_report_id: int | None = Field(None, ge=1)

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
    page: int = Field(1, ge=1)
    size: int = Field(10, ge=1, le=100)
