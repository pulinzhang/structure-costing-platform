"""LLM 分析报告响应 VO。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class LlmAnalysisScopeVO(BaseModel):
    location: str
    year: int
    month: int
    vehicle_model: str
    bom_version: str
    part_number: str | None = None
    stamping_supplier: str | None = None


class LlmAnalysisReportMetadataVO(BaseModel):
    engine_run_id: int | None = None
    has_data: bool = True
    data_message: str | None = None
    generated_at: datetime | None = None
    llm_model: str | None = None
    prompt_version: str | None = None
    prompt_hash: str | None = None
    context_pack_ids: list[str] = Field(default_factory=list)
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    from_cache: bool = False
    audit_hint: str | None = None
    resolved_report_type: str | None = None
    intent_source: str | None = None
    user_question: str | None = None

    @field_serializer("generated_at")
    def _ser_dt(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None


class LlmAnalysisReportTaskVO(BaseModel):
    """创建任务受理 / 轮询摘要。"""

    task_id: str
    report_id: int
    status: str
    report_type: str
    resolved_report_type: str | None = None
    scope: LlmAnalysisScopeVO
    from_cache: bool = False
    progress_percent: int = 0
    message: str = ""


class LlmAnalysisReportVO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_id: int
    task_id: str
    report_type: str
    resolved_report_type: str
    audience: str
    user_question: str
    prompt_id: str | None = None
    intent_source: str
    scope: LlmAnalysisScopeVO
    status: str
    markdown_content: str | None = None
    error_message: str | None = None
    metadata: LlmAnalysisReportMetadataVO
    attachments: dict[str, Any] | None = None

    @classmethod
    def from_orm_row(
        cls,
        row: object,
        *,
        from_cache: bool = False,
        attachments: dict[str, Any] | None = None,
        pack_ids: list[str] | None = None,
    ) -> "LlmAnalysisReportVO":
        import json

        context_pack_ids: list[str] = pack_ids or []
        raw_ids = getattr(row, "context_pack_ids", None)
        if raw_ids:
            try:
                parsed = json.loads(raw_ids)
                if isinstance(parsed, list):
                    context_pack_ids = [str(item) for item in parsed]
                elif isinstance(parsed, dict):
                    analyses = parsed.get("analyses") or []
                    if isinstance(analyses, list):
                        context_pack_ids = [str(item) for item in analyses]
            except (TypeError, ValueError, json.JSONDecodeError):
                context_pack_ids = []

        from app.services.llm.prompts.labels import sanitize_report_markdown

        raw_markdown = getattr(row, "markdown_content", None)
        markdown_content = (
            sanitize_report_markdown(str(raw_markdown))
            if raw_markdown
            else None
        )

        return cls(
            report_id=int(getattr(row, "id")),
            task_id=str(getattr(row, "task_id")),
            report_type=str(getattr(row, "report_type")),
            resolved_report_type=str(getattr(row, "resolved_report_type")),
            audience=str(getattr(row, "audience")),
            user_question=str(getattr(row, "user_question")),
            prompt_id=getattr(row, "prompt_id", None),
            intent_source=str(getattr(row, "intent_source")),
            scope=LlmAnalysisScopeVO(
                location=str(getattr(row, "location")),
                year=int(getattr(row, "year")),
                month=int(getattr(row, "month")),
                vehicle_model=str(getattr(row, "vehicle_model")),
                bom_version=str(getattr(row, "bom_version")),
                part_number=getattr(row, "part_number", None),
                stamping_supplier=getattr(row, "stamping_supplier", None),
            ),
            status=str(getattr(row, "status")),
            markdown_content=markdown_content,
            error_message=getattr(row, "error_message", None),
            metadata=LlmAnalysisReportMetadataVO(
                engine_run_id=getattr(row, "engine_run_id", None),
                has_data=bool(getattr(row, "has_data", 1)),
                data_message=getattr(row, "data_message", None),
                generated_at=getattr(row, "updated_at", None),
                llm_model=getattr(row, "llm_model", None),
                prompt_version=getattr(row, "prompt_version", None),
                prompt_hash=getattr(row, "prompt_hash", None),
                context_pack_ids=context_pack_ids,
                prompt_tokens=getattr(row, "prompt_tokens", None),
                completion_tokens=getattr(row, "completion_tokens", None),
                total_tokens=getattr(row, "total_tokens", None),
                from_cache=from_cache,
                audit_hint=getattr(row, "audit_hint", None),
                resolved_report_type=str(getattr(row, "resolved_report_type")),
                intent_source=str(getattr(row, "intent_source")),
                user_question=str(getattr(row, "user_question")),
            ),
            attachments=attachments,
        )


class LlmScopeOptionsVO(BaseModel):
    locations: list[str] = Field(default_factory=list)
    vehicle_models: list[str] = Field(default_factory=list)
    bom_versions: list[str] = Field(default_factory=list)
    years: list[int] = Field(default_factory=list)
