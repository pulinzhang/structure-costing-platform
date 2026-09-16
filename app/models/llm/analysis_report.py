"""LLM 分析报告表（仅本切片落库；禁止写核价金额结果）。"""

from __future__ import annotations

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.common.audit_mixin import AuditUserMixin


class LlmAnalysisReport(AuditUserMixin, Base):
    """一次分析报告（与 AsyncTask 通过 task_id 关联）。"""

    __tablename__ = "llm_analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    task_id: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True, comment="AsyncTask ID"
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True, comment="提交用户 ID")

    report_type: Mapped[str] = mapped_column(
        String(40), nullable=False, comment="请求类型（可含 auto）"
    )
    resolved_report_type: Mapped[str] = mapped_column(
        String(40), nullable=False, comment="解析后的类型"
    )
    audience: Mapped[str] = mapped_column(String(40), nullable=False, comment="受众")
    user_question: Mapped[str] = mapped_column(Text, nullable=False, comment="用户问题原文")
    prompt_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    intent_source: Mapped[str] = mapped_column(
        String(40), nullable=False, default="chip", comment="chip|rule|default_dashboard"
    )

    location: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(50), nullable=False)
    bom_version: Mapped[str] = mapped_column(String(20), nullable=False)
    part_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stamping_supplier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    engine_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending|running|succeeded|failed",
    )
    markdown_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    idempotency_key: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True, comment="含问题指纹"
    )

    prompt_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    context_pack_ids: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="JSON 数组字符串"
    )
    has_data: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="1=有数据 0=无"
    )
    data_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    audit_hint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True, comment="全链路追踪 ID"
    )
    prompt_preview: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Prompt 前 500 字符（审计）"
    )
    llm_response_preview: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="LLM 响应前 500 字符（审计）"
    )
    query_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="解析后的 AnalysisQuery JSON，供下一问沿用"
    )

    __table_args__ = (
        Index(
            "ix_llm_reports_user_idempotency",
            "user_id",
            "idempotency_key",
        ),
        Index(
            "ix_llm_reports_scope",
            "location",
            "year",
            "month",
            "vehicle_model",
            "bom_version",
        ),
    )
