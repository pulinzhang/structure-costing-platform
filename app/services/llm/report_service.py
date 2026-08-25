"""LlmAnalysisReportService：Query → Repository → Analysis → Snapshot → LLM。"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.config import settings
from app.database import DatabaseConfig
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
from app.schemas.llm.analysis_query import AnalysisQuery
from app.schemas.vo.async_task_vo import AsyncTaskProgressVO
from app.schemas.vo.llm_analysis_vo import (
    LlmAnalysisReportListItemVO,
    LlmAnalysisReportTaskVO,
    LlmAnalysisReportVO,
    LlmAnalysisScopeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.async_task import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    AsyncTaskService,
)
from app.services.llm.analysis.idempotency import build_idempotency_key
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.engine_readiness import EngineReadinessRunner
from app.services.llm.usage import UsageHelpRunner
from app.services.llm.client import LlmClientError
from app.services.llm.context.snapshot_builder import SnapshotBuilder
from app.services.llm.generator import LlmReportGenerator
from app.services.llm.query.query_parser import QueryParser
from app.utils.logging_config import get_logger

logger = get_logger("service.llm.report")

TASK_TYPE_LLM_ANALYSIS_REPORT = "llm_analysis_report"
REPORT_STATUS_PENDING = "pending"
REPORT_STATUS_RUNNING = "running"
REPORT_STATUS_SUCCEEDED = "succeeded"
REPORT_STATUS_FAILED = "failed"

_async_task_service = AsyncTaskService()


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
        analysis_query = self.query_parser.parse(
            db,
            user_question=dto.user_question,
        )
        active_count = self.repository.count_active_by_user(
            db, user_id=int(current_user.id)
        )
        if active_count >= int(settings.LLM_MAX_CONCURRENT_TASKS_PER_USER):
            raise BusinessException("too many requests", code=429)

        trace_id = str(uuid.uuid4())
        analysis_query = analysis_query.model_copy(update={"trace_id": trace_id})
        audience = (dto.audience or "buyer_lead").strip() or "buyer_lead"
        part_number = analysis_query.part_number()
        analyses_key = analysis_query.analyses_key()
        # 表字段 NOT NULL：未抽到时用占位，真实过滤仍以 AnalysisQuery.filters 为准
        location = analysis_query.location() or "未指定"
        vehicle_model = analysis_query.vehicle_model() or "未指定"
        bom_version = analysis_query.bom_version() or "未指定"
        idem_key = dto.idempotency_key or build_idempotency_key(
            report_type="auto",
            audience=audience,
            location=location,
            year=analysis_query.time_range.end_year,
            month=analysis_query.time_range.end_month,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            user_question=dto.user_question,
            user_id=int(current_user.id),
            part_number=part_number,
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
        # 落库：year/month 取区间终点（兼容现表结构）；完整 Query JSON 交给 worker
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
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            ),
        )
        db.commit()

        # 把完整 query JSON 暂存到 data_message 不合适；worker 内重新 parse
        AsyncTaskService.submit(
            self._process_in_background,
            task.task_id,
            int(row.id),
            str(audit["updated_by"]),
            json.dumps(analysis_query.model_dump(mode="json"), ensure_ascii=False),
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
        return LlmAnalysisReportVO.from_orm_row(row)

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
            skip=query.skip,
            limit=query.limit,
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

    def _process_in_background(
        self,
        task_id: str,
        report_id: int,
        updated_by: str,
        analysis_query_json: str,
    ) -> None:
        session_factory = DatabaseConfig.get_session_factory()
        db = session_factory()
        try:
            from app.schemas.llm.analysis_query import AnalysisQuery

            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_RUNNING,
                progress=5,
                message="开始分析…",
            )
            self.repository.mark_running(db, report_id, updated_by=updated_by)
            db.commit()

            row = self.repository.get_by_id(db, report_id)
            if row is None:
                raise RuntimeError(f"报告不存在: {report_id}")

            analysis_query = AnalysisQuery.model_validate(
                json.loads(analysis_query_json)
            )
            if not analysis_query.trace_id:
                analysis_query = analysis_query.model_copy(
                    update={"trace_id": str(uuid.uuid4())}
                )

            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_RUNNING,
                progress=25,
                message=(
                    "正在检索帮助语料…"
                    if analysis_query.query_mode == "usage_help"
                    else "正在检查核算就绪…"
                    if analysis_query.query_mode == "engine_readiness"
                    else "正在查询并聚合核价事实…"
                ),
            )
            if analysis_query.query_mode == "usage_help":
                run = self.usage_runner.run(analysis_query)
            elif analysis_query.query_mode == "engine_readiness":
                run = self.engine_readiness_runner.run(db, analysis_query)
            else:
                run = self.runner.run(db, analysis_query)
            snapshot = self.snapshot_builder.build(
                query=analysis_query, run=run
            )

            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_RUNNING,
                progress=55,
                message=(
                    "正在生成操作说明…"
                    if analysis_query.query_mode == "usage_help"
                    else "正在生成就绪说明…"
                    if analysis_query.query_mode == "engine_readiness"
                    else "AI正在思考中…"
                ),
            )
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
                from app.services.llm.prompts.registry import PromptRegistry

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
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_COMPLETED,
                progress=100,
                message=(
                    "帮助回答完成"
                    if analysis_query.query_mode == "usage_help"
                    else "分析完成"
                ),
                result={
                    "report_id": report_id,
                    "status": REPORT_STATUS_SUCCEEDED,
                    "analyses": analysis_query.analyses,
                },
            )
        except Exception as exc:
            logger.exception("LLM 分析任务失败 task_id=%s", task_id)
            try:
                db.rollback()
            except Exception:
                pass
            try:
                self.repository.mark_failed(
                    db,
                    report_id,
                    LlmAnalysisReportFailPatch(
                        status=REPORT_STATUS_FAILED,
                        error_message=str(exc)[:1000],
                        updated_by=updated_by,
                    ),
                )
                db.commit()
            except Exception:
                logger.exception("写入失败状态出错")
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_FAILED,
                progress=100,
                message=f"分析失败: {exc}",
                result={"report_id": report_id, "status": REPORT_STATUS_FAILED},
            )
        finally:
            db.close()

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
        elif row.status == REPORT_STATUS_SUCCEEDED:
            progress = 100
        elif row.status == REPORT_STATUS_FAILED:
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
        )
