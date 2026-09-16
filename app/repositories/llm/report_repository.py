"""LLM 分析报告 Repository — 仅 llm_analysis_reports。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.orm import Session

from app.common.timezone import now
from app.models.llm import LlmAnalysisReport


@dataclass(frozen=True, slots=True)
class LlmAnalysisReportInsert:
    task_id: str
    user_id: int
    report_type: str
    resolved_report_type: str
    audience: str
    user_question: str
    prompt_id: str | None
    intent_source: str
    location: str
    year: int
    month: int
    vehicle_model: str
    bom_version: str
    part_number: str | None
    stamping_supplier: str | None
    engine_run_id: int | None
    status: str
    idempotency_key: str
    trace_id: str | None
    query_json: str | None
    created_by: str
    updated_by: str


@dataclass(frozen=True, slots=True)
class LlmAnalysisReportSuccessPatch:
    status: str
    markdown_content: str
    prompt_version: str
    prompt_hash: str
    llm_model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    context_pack_ids: str
    has_data: int
    data_message: str | None
    audit_hint: str | None
    prompt_preview: str | None
    llm_response_preview: str | None
    updated_by: str


@dataclass(frozen=True, slots=True)
class LlmAnalysisReportFailPatch:
    status: str
    error_message: str
    updated_by: str


class LlmAnalysisReportRepository:
    def get_by_id(self, db: Session, report_id: int) -> LlmAnalysisReport | None:
        return db.query(LlmAnalysisReport).filter(LlmAnalysisReport.id == report_id).first()

    def get_by_task_id(self, db: Session, task_id: str) -> LlmAnalysisReport | None:
        return db.query(LlmAnalysisReport).filter(LlmAnalysisReport.task_id == task_id).first()

    def count_active_by_user(self, db: Session, *, user_id: int) -> int:
        return (
            db.query(LlmAnalysisReport)
            .filter(
                LlmAnalysisReport.user_id == user_id,
                LlmAnalysisReport.status.in_(("pending", "running")),
            )
            .count()
        )

    def find_idempotent_hit(
        self,
        db: Session,
        *,
        user_id: int,
        idempotency_key: str,
        ttl_minutes: int = 5,
    ) -> LlmAnalysisReport | None:
        """TTL 内同用户同 key 的 succeeded / running / pending。"""
        cutoff = now() - timedelta(minutes=ttl_minutes)
        return (
            db.query(LlmAnalysisReport)
            .filter(
                LlmAnalysisReport.user_id == user_id,
                LlmAnalysisReport.idempotency_key == idempotency_key,
                LlmAnalysisReport.status.in_(("pending", "running", "succeeded")),
                LlmAnalysisReport.created_at >= cutoff,
            )
            .order_by(LlmAnalysisReport.id.desc())
            .first()
        )

    def create(self, db: Session, payload: LlmAnalysisReportInsert) -> LlmAnalysisReport:
        row = LlmAnalysisReport(
            task_id=payload.task_id,
            user_id=payload.user_id,
            report_type=payload.report_type,
            resolved_report_type=payload.resolved_report_type,
            audience=payload.audience,
            user_question=payload.user_question,
            prompt_id=payload.prompt_id,
            intent_source=payload.intent_source,
            location=payload.location,
            year=payload.year,
            month=payload.month,
            vehicle_model=payload.vehicle_model,
            bom_version=payload.bom_version,
            part_number=payload.part_number,
            stamping_supplier=payload.stamping_supplier,
            engine_run_id=payload.engine_run_id,
            status=payload.status,
            idempotency_key=payload.idempotency_key,
            trace_id=payload.trace_id,
            query_json=payload.query_json,
            created_by=payload.created_by,
            updated_by=payload.updated_by,
        )
        db.add(row)
        db.flush()
        db.refresh(row)
        return row

    def mark_running(self, db: Session, report_id: int, *, updated_by: str) -> None:
        row = self.get_by_id(db, report_id)
        if row is None:
            return
        row.status = "running"
        row.updated_by = updated_by
        db.flush()

    def mark_succeeded(
        self,
        db: Session,
        report_id: int,
        patch: LlmAnalysisReportSuccessPatch,
    ) -> LlmAnalysisReport | None:
        row = self.get_by_id(db, report_id)
        if row is None:
            return None
        row.status = patch.status
        row.markdown_content = patch.markdown_content
        row.error_message = None
        row.prompt_version = patch.prompt_version
        row.prompt_hash = patch.prompt_hash
        row.llm_model = patch.llm_model
        row.prompt_tokens = patch.prompt_tokens
        row.completion_tokens = patch.completion_tokens
        row.total_tokens = patch.total_tokens
        row.context_pack_ids = patch.context_pack_ids
        row.has_data = patch.has_data
        row.data_message = patch.data_message
        row.audit_hint = patch.audit_hint
        row.prompt_preview = patch.prompt_preview
        row.llm_response_preview = patch.llm_response_preview
        row.updated_by = patch.updated_by
        db.flush()
        db.refresh(row)
        return row

    def mark_failed(
        self,
        db: Session,
        report_id: int,
        patch: LlmAnalysisReportFailPatch,
    ) -> LlmAnalysisReport | None:
        row = self.get_by_id(db, report_id)
        if row is None:
            return None
        row.status = patch.status
        row.error_message = patch.error_message
        row.updated_by = patch.updated_by
        db.flush()
        db.refresh(row)
        return row

    def paginate(
        self,
        db: Session,
        *,
        user_id: int | None = None,
        location: str | None = None,
        year: int | None = None,
        month: int | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        report_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[LlmAnalysisReport], int]:
        q = db.query(LlmAnalysisReport)
        if user_id is not None:
            q = q.filter(LlmAnalysisReport.user_id == user_id)
        if location:
            q = q.filter(LlmAnalysisReport.location == location)
        if year is not None:
            q = q.filter(LlmAnalysisReport.year == year)
        if month is not None:
            q = q.filter(LlmAnalysisReport.month == month)
        if vehicle_model:
            q = q.filter(LlmAnalysisReport.vehicle_model == vehicle_model)
        if bom_version:
            q = q.filter(LlmAnalysisReport.bom_version == bom_version)
        if report_type:
            q = q.filter(LlmAnalysisReport.resolved_report_type == report_type)
        if status:
            q = q.filter(LlmAnalysisReport.status == status)
        total = q.count()
        rows = q.order_by(LlmAnalysisReport.id.desc()).offset(skip).limit(limit).all()
        return rows, total

    def delete_by_id(self, db: Session, report_id: int) -> bool:
        row = self.get_by_id(db, report_id)
        if row is None:
            return False
        db.delete(row)
        db.flush()
        return True
