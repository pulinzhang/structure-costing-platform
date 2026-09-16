"""LlmAnalysisReportService：Query → Repository → Analysis → Snapshot → LLM。"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.config import settings
from app.exceptions.base import BusinessException, NotFoundException, PermissionException
from app.repositories.llm import (
    LlmAnalysisReportFailPatch,
    LlmAnalysisReportInsert,
    LlmAnalysisReportRepository,
    LlmAnalysisReportSuccessPatch,
)
from app.schemas.dto.llm_analysis_dto import (
    LlmAnalysisReportCreateDTO,
    LlmAnalysisReportQuery,
)
from app.schemas.llm.analysis_query import SCOPE_UNSET, AnalysisQuery, QueryMode, TimeRange
from app.schemas.vo.async_task_vo import AsyncTaskProgressVO
from app.schemas.vo.llm_analysis_vo import (
    LlmAnalysisCarryVO,
    LlmAnalysisReportListItemVO,
    LlmAnalysisReportTaskVO,
    LlmAnalysisReportVO,
    LlmAnalysisScopeVO,
    LlmAnalysisTimeRangeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    AsyncTaskService,
    ProgressCallback,
    WorkerTaskOutcome,
)
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.analysis.shared.idempotency import build_idempotency_key
from app.services.llm.client import LlmClientError
from app.services.llm.comparison_basis import default_comparison_basis
from app.services.llm.context.snapshot_builder import SnapshotBuilder
from app.services.llm.engine_readiness import EngineReadinessRunner
from app.services.llm.generator import LlmReportGenerator
from app.services.llm.prompts.labels import sanitize_report_markdown
from app.services.llm.prompts.registry import PromptRegistry
from app.services.llm.query.intent_router import detect_audience
from app.services.llm.query.query_parser import QueryParser
from app.services.llm.usage import UsageHelpRunner
from app.utils.logging_config import get_logger

logger = get_logger("service.llm.report")

TASK_TYPE_LLM_ANALYSIS_REPORT = "llm_analysis_report"
REPORT_STATUS_PENDING = "pending"
REPORT_STATUS_RUNNING = "running"
REPORT_STATUS_SUCCEEDED = "succeeded"
REPORT_STATUS_FAILED = "failed"

_async_task_service = AsyncTaskService()


def _mode_progress_copy(query_mode: str) -> tuple[str, str, str]:
    if query_mode == "usage_help":
        return ("正在检索帮助语料…", "正在生成操作说明…", "帮助回答完成")
    if query_mode == "engine_readiness":
        return ("正在检查核算就绪…", "正在生成就绪说明…", "分析完成")
    return ("正在查询并聚合核价事实…", "AI正在思考中…", "分析完成")


def analysis_query_from_report_fields(
    *,
    query_json: str | None,
    location: str,
    year: int,
    month: int,
    vehicle_model: str,
    bom_version: str,
    part_number: str | None,
    resolved_report_type: str,
    user_question: str = "",
) -> AnalysisQuery | None:
    """沿用上一问：优先 query_json。扁字段只还原加列前的旧行，不要当主路径改。"""
    if query_json:
        try:
            parsed: Any = json.loads(query_json)
        except (TypeError, ValueError, json.JSONDecodeError):
            parsed = None
        if isinstance(parsed, dict):
            try:
                return AnalysisQuery.model_validate(parsed)
            except (TypeError, ValueError):
                pass

    try:
        month_key = f"{int(year):04d}-{int(month):02d}"
    except (TypeError, ValueError):
        return None
    filters: dict[str, str] = {}
    if location and location != SCOPE_UNSET:
        filters["location"] = location
    if vehicle_model and vehicle_model != SCOPE_UNSET:
        filters["vehicle_model"] = vehicle_model
    if bom_version and bom_version != SCOPE_UNSET:
        filters["bom_version"] = bom_version
    if part_number:
        filters["part_number"] = part_number

    report_type = (resolved_report_type or "").strip()
    query_mode: QueryMode = "analysis"
    subject = "cost_total"
    if report_type == "usage_help":
        query_mode = "usage_help"
        subject = "usage_help"
    elif report_type == "engine_readiness":
        query_mode = "engine_readiness"
        subject = "engine_readiness"

    return AnalysisQuery(
        time_range=TimeRange(start=month_key, end=month_key),
        filters=filters,
        subject=subject,
        comparison_basis=default_comparison_basis(same_bom_version=True),
        analyses=["summary"],
        user_question=user_question,
        query_mode=query_mode,
    )


class LlmAnalysisReportService:
    def __init__(self) -> None:
        self.repository = LlmAnalysisReportRepository()
        self.query_parser = QueryParser()
        self.runner = AnalysisRunner()
        self.usage_runner = UsageHelpRunner()
        self.engine_readiness_runner = EngineReadinessRunner()
        self.snapshot_builder = SnapshotBuilder()
        self.generator = LlmReportGenerator()

    def create_report(
        self,
        db: Session,
        dto: LlmAnalysisReportCreateDTO,
        *,
        current_user: UserVO,
    ) -> LlmAnalysisReportTaskVO:
        previous_query = self._load_previous_query(
            db,
            previous_report_id=dto.previous_report_id,
            current_user=current_user,
        )
        analysis_query = self.query_parser.parse(
            db,
            user_question=dto.user_question,
            previous_query=previous_query,
        )
        active_count = self.repository.count_active_by_user(db, user_id=int(current_user.id))
        if active_count >= int(settings.LLM_MAX_CONCURRENT_TASKS_PER_USER):
            raise BusinessException("too many requests", code=429)

        trace_id = str(uuid.uuid4())
        analysis_query = analysis_query.model_copy(update={"trace_id": trace_id})
        audience = detect_audience(dto.user_question, dto.audience)
        part_number = analysis_query.part_number()
        analyses_key = analysis_query.analyses_key()
        # 表字段 NOT NULL：未抽到时用 SCOPE_UNSET，真实过滤仍以 AnalysisQuery.filters 为准
        location = analysis_query.location() or SCOPE_UNSET
        vehicle_model = analysis_query.vehicle_model() or SCOPE_UNSET
        bom_version = analysis_query.bom_version() or SCOPE_UNSET
        idem_key = dto.idempotency_key or build_idempotency_key(
            report_type="auto",
            audience=audience,
            user_question=dto.user_question,
            user_id=int(current_user.id),
            time_range_start=analysis_query.time_range.start,
            time_range_end=analysis_query.time_range.end,
            filters=dict(analysis_query.filters),
        )

        if not dto.force_refresh:
            hit = self.repository.find_idempotent_hit(
                db,
                user_id=int(current_user.id),
                idempotency_key=idem_key,
                ttl_minutes=int(settings.LLM_IDEMPOTENCY_TTL_MINUTES),
            )
            if hit is not None:
                return self._to_task_vo(hit, from_cache=True, message="命中幂等缓存")

        audit = audit_create(current_user)
        task = _async_task_service.create_task(
            task_type=TASK_TYPE_LLM_ANALYSIS_REPORT,
            message="已提交分析队列",
            operator_id=int(current_user.id),
            operator_name=display_name(current_user),
        )
        query_json = json.dumps(analysis_query.model_dump(mode="json"), ensure_ascii=False)
        row = self.repository.create(
            db,
            LlmAnalysisReportInsert(
                task_id=task.task_id,
                user_id=int(current_user.id),
                report_type="auto",
                resolved_report_type=analyses_key,
                audience=audience,
                user_question=dto.user_question,
                prompt_id=None,
                intent_source="nl_condition_extract",
                location=location,
                year=analysis_query.time_range.end_year,
                month=analysis_query.time_range.end_month,
                vehicle_model=vehicle_model,
                bom_version=bom_version,
                part_number=part_number,
                stamping_supplier=None,
                engine_run_id=None,
                status=REPORT_STATUS_PENDING,
                idempotency_key=idem_key,
                trace_id=trace_id,
                query_json=query_json,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            ),
        )
        db.commit()

        report_id = int(row.id)
        updated_by = str(audit["updated_by"])

        def work(worker_db: Session, on_progress: ProgressCallback) -> WorkerTaskOutcome:
            return self._run_report_work(
                worker_db,
                on_progress,
                report_id=report_id,
                updated_by=updated_by,
                analysis_query_json=query_json,
            )

        def on_crash(worker_db: Session, error: BaseException) -> None:
            try:
                self.repository.mark_failed(
                    worker_db,
                    report_id,
                    LlmAnalysisReportFailPatch(
                        status=REPORT_STATUS_FAILED,
                        error_message=str(error)[:1000],
                        updated_by=updated_by,
                    ),
                )
                worker_db.commit()
            except Exception:
                logger.exception("写入失败状态出错")

        _async_task_service.submit_session_worker(
            task.task_id,
            start_message="开始分析…",
            work=work,
            on_crash=on_crash,
            crash_message=lambda error: f"分析失败: {error}",
            crash_progress=100,
            crash_result=lambda _error: {
                "report_id": report_id,
                "status": REPORT_STATUS_FAILED,
            },
        )
        return self._to_task_vo(row, from_cache=False, message=self._submit_message(analysis_query))

    def _submit_message(self, analysis_query: AnalysisQuery) -> str:
        if analysis_query.query_mode == "usage_help":
            return "正在检索帮助语料…"
        return "正在查询核价结果…"

    def get_report(
        self,
        db: Session,
        report_id: int,
        *,
        current_user: UserVO,
    ) -> LlmAnalysisReportVO:
        row = self.repository.get_by_id(db, report_id)
        if row is None:
            raise NotFoundException("报告不存在")
        if int(row.user_id) != int(current_user.id):
            raise PermissionException("只能查看本人的分析报告")
        return self._report_vo(row)

    def list_reports(
        self,
        db: Session,
        query: LlmAnalysisReportQuery,
        *,
        current_user: UserVO,
    ) -> tuple[list[LlmAnalysisReportListItemVO], int]:
        rows, total = self.repository.paginate(
            db,
            user_id=int(current_user.id),
            location=query.location,
            year=query.year,
            month=query.month,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            report_type=query.report_type,
            status=query.status,
            skip=(query.page - 1) * query.size,
            limit=query.size,
        )
        return [LlmAnalysisReportListItemVO.from_orm_row(row) for row in rows], total

    def delete_report(
        self,
        db: Session,
        report_id: int,
        *,
        current_user: UserVO,
    ) -> None:
        """删除分析报告；只能删除本人的记录（管理员也不能删他人）。"""
        row = self.repository.get_by_id(db, report_id)
        if row is None:
            raise NotFoundException("报告不存在")
        if int(row.user_id) != int(current_user.id):
            raise PermissionException("只能删除本人的分析报告")
        self.repository.delete_by_id(db, report_id)
        db.commit()

    def get_task_progress(
        self,
        db: Session,
        task_id: str,
        *,
        current_user: UserVO,
    ) -> AsyncTaskProgressVO:
        snapshot = _async_task_service.get_task_snapshot(task_id)
        if snapshot is None:
            raise NotFoundException("任务不存在")
        row = self.repository.get_by_task_id(db, task_id)
        if row is None:
            raise NotFoundException("任务不存在")
        if int(row.user_id) != int(current_user.id):
            raise PermissionException("只能查看本人的分析任务")
        result = AsyncTaskService.parse_result_json(snapshot.get("result_json"))
        return AsyncTaskProgressVO.from_snapshot(snapshot, result=result)

    def _run_report_work(
        self,
        db: Session,
        on_progress: ProgressCallback,
        *,
        report_id: int,
        updated_by: str,
        analysis_query_json: str,
    ) -> WorkerTaskOutcome:
        self.repository.mark_running(db, report_id, updated_by=updated_by)
        db.commit()

        row = self.repository.get_by_id(db, report_id)
        if row is None:
            raise RuntimeError(f"报告不存在: {report_id}")

        analysis_query = AnalysisQuery.model_validate(json.loads(analysis_query_json))
        if not analysis_query.trace_id:
            analysis_query = analysis_query.model_copy(update={"trace_id": str(uuid.uuid4())})

        fetch_message, generate_message, done_message = _mode_progress_copy(
            analysis_query.query_mode
        )
        on_progress(25, fetch_message)
        if analysis_query.query_mode == "usage_help":
            run = self.usage_runner.run(analysis_query)
        elif analysis_query.query_mode == "engine_readiness":
            run = self.engine_readiness_runner.run(db, analysis_query)
        else:
            run = self.runner.run(db, analysis_query)
        snapshot = self.snapshot_builder.build(query=analysis_query, run=run)

        on_progress(55, generate_message)
        try:
            generated = self.generator.generate(
                snapshot=snapshot,
                audience=row.audience,
            )
            markdown = generated.markdown_content
            llm_model = generated.llm_model
            prompt_version = generated.prompt_version
            prompt_hash = generated.prompt_hash
            prompt_tokens = generated.prompt_tokens
            completion_tokens = generated.completion_tokens
            total_tokens = generated.total_tokens
            prompt_preview = generated.prompt_preview
            llm_response_preview = generated.llm_response_preview
        except LlmClientError as exc:
            logger.warning("LLM 调用失败，降级规则模板: %s", exc)
            markdown = self.generator.render_fallback_markdown(
                snapshot=snapshot,
                error_hint=str(exc),
            )
            llm_model = None
            prompt = PromptRegistry().resolve(row.audience)
            prompt_version = prompt.prompt_version
            prompt_hash = prompt.prompt_hash
            prompt_tokens = None
            completion_tokens = None
            total_tokens = None
            prompt_preview = None
            llm_response_preview = None

        self.repository.mark_succeeded(
            db,
            report_id,
            LlmAnalysisReportSuccessPatch(
                status=REPORT_STATUS_SUCCEEDED,
                markdown_content=markdown,
                prompt_version=prompt_version,
                prompt_hash=prompt_hash,
                llm_model=llm_model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                context_pack_ids=json.dumps(
                    {
                        "analyses": analysis_query.analyses,
                        "trace_id": analysis_query.trace_id,
                        "analysis_version": snapshot.meta.analysis_version,
                    },
                    ensure_ascii=False,
                ),
                has_data=1 if snapshot.meta.has_data else 0,
                data_message=snapshot.meta.data_message,
                audit_hint=None,
                prompt_preview=prompt_preview,
                llm_response_preview=llm_response_preview,
                updated_by=updated_by,
            ),
        )
        db.commit()
        return WorkerTaskOutcome(
            status=STATUS_COMPLETED,
            progress=100,
            message=done_message,
            result={
                "report_id": report_id,
                "status": REPORT_STATUS_SUCCEEDED,
                "analyses": analysis_query.analyses,
            },
        )

    def _to_task_vo(
        self,
        row: Any,
        *,
        from_cache: bool,
        message: str,
    ) -> LlmAnalysisReportTaskVO:
        status_map = {
            REPORT_STATUS_PENDING: "processing",
            REPORT_STATUS_RUNNING: "processing",
            REPORT_STATUS_SUCCEEDED: "succeeded",
            REPORT_STATUS_FAILED: "failed",
        }
        progress = 0
        if row.status == REPORT_STATUS_RUNNING:
            progress = 40
        elif row.status == REPORT_STATUS_SUCCEEDED or row.status == REPORT_STATUS_FAILED:
            progress = 100
        return LlmAnalysisReportTaskVO(
            task_id=row.task_id,
            report_id=int(row.id),
            status=status_map.get(row.status, row.status),
            report_type=row.report_type,
            resolved_report_type=row.resolved_report_type,
            scope=LlmAnalysisScopeVO(
                location=row.location,
                year=row.year,
                month=row.month,
                vehicle_model=row.vehicle_model,
                bom_version=row.bom_version,
                part_number=row.part_number,
                stamping_supplier=row.stamping_supplier,
            ),
            from_cache=from_cache,
            progress_percent=progress,
            message=message,
            carry=self._carry_from_row(row),
        )

    def _load_previous_query(
        self,
        db: Session,
        *,
        previous_report_id: int | None,
        current_user: UserVO,
    ) -> AnalysisQuery | None:
        if previous_report_id is None:
            return None
        row = self.repository.get_by_id(db, previous_report_id)
        if row is None or int(row.user_id) != int(current_user.id):
            return None
        return self._query_from_row(row)

    @staticmethod
    def _query_from_row(row: Any) -> AnalysisQuery | None:
        return analysis_query_from_report_fields(
            query_json=getattr(row, "query_json", None),
            location=str(getattr(row, "location", "") or ""),
            year=int(getattr(row, "year", 0) or 0),
            month=int(getattr(row, "month", 0) or 0),
            vehicle_model=str(getattr(row, "vehicle_model", "") or ""),
            bom_version=str(getattr(row, "bom_version", "") or ""),
            part_number=getattr(row, "part_number", None),
            resolved_report_type=str(getattr(row, "resolved_report_type", "") or ""),
            user_question=str(getattr(row, "user_question", "") or ""),
        )

    @classmethod
    def _carry_from_row(cls, row: Any) -> LlmAnalysisCarryVO | None:
        query = cls._query_from_row(row)
        if query is None:
            return None
        return LlmAnalysisCarryVO(
            time_range=LlmAnalysisTimeRangeVO(
                start=query.time_range.start,
                end=query.time_range.end,
            ),
            filters=dict(query.filters),
            subject=query.subject,
            query_mode=query.query_mode,
        )

    @classmethod
    def _report_vo(cls, row: Any) -> LlmAnalysisReportVO:
        # carry 要从 query_json 还原，不塞进 from_orm_row（VO 不解析 Query）。
        vo = LlmAnalysisReportVO.from_orm_row(row)
        carry = cls._carry_from_row(row)
        markdown = vo.markdown_content
        updates: dict[str, Any] = {"carry": carry}
        if isinstance(markdown, str) and markdown:
            updates["markdown_content"] = sanitize_report_markdown(markdown)
        return vo.model_copy(update=updates)
