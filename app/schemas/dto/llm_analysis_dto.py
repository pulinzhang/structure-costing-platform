"""LLM 分析报告请求 DTO。"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class LlmAnalysisScopeDTO(BaseModel):
    location: str = Field(..., min_length=1, max_length=50)
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    vehicle_model: str = Field(..., min_length=1, max_length=50)
    bom_version: str = Field(..., min_length=1, max_length=20)
    part_number: str | None = Field(None, max_length=50)
    stamping_supplier: str | None = Field(None, max_length=50)

    @field_validator(
        "location",
        "vehicle_model",
        "bom_version",
        "part_number",
        "stamping_supplier",
        mode="before",
    )
    @classmethod
    def _strip_optional(cls, value: object) -> object:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class LlmAnalysisReportCreateDTO(BaseModel):
    """POST /api/llm/reports"""

    report_type: str = Field(
        ...,
        min_length=1,
        max_length=40,
        description="dashboard|steel|…|auto",
    )
    user_question: str = Field(..., min_length=1, max_length=2000)
    scope: LlmAnalysisScopeDTO
    audience: str | None = Field(None, max_length=40)
    prompt_id: str | None = Field(None, max_length=40)
    engine_run_id: int | None = None
    idempotency_key: str | None = Field(None, max_length=200)
    force_refresh: bool = False

    @field_validator("user_question", "report_type", "audience", "prompt_id", mode="before")
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
