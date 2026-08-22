"""
LlmAnalysisReportService：幂等、AsyncTask、落库报告。
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.common.audit import audit_create, display_name
from app.config import settings
from app.database import DatabaseConfig
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
from app.schemas.vo.async_task_vo import AsyncTaskProgressVO
from app.schemas.vo.llm_analysis_vo import (
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
from app.services.llm.analysis.generator import LlmReportGenerator
from app.services.llm.analysis.idempotency import build_idempotency_key
from app.services.llm.analysis.intent_resolver import resolve_intent
from app.services.llm.client import LlmClientError
from app.services.llm.context.aggregator import AnalysisScope, LlmContextAggregator
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
        self.aggregator = LlmContextAggregator()
        self.generator = LlmReportGenerator()

    def create_report(
        self,
        db: Session,
        dto: LlmAnalysisReportCreateDTO,
        *,
        current_user: UserVO,
    ) -> LlmAnalysisReportTaskVO:
        intent = resolve_intent(
            report_type=dto.report_type,
            user_question=dto.user_question,
            audience=dto.audience,
            prompt_id=dto.prompt_id,
            scope_part_number=dto.scope.part_number,
        )
        part_number = intent.part_number or dto.scope.part_number
        idem_key = dto.idempotency_key or build_idempotency_key(
            report_type=intent.requested_report_type,
            audience=intent.audience,
            location=dto.scope.location,
            year=dto.scope.year,
            month=dto.scope.month,
            vehicle_model=dto.scope.vehicle_model,
            bom_version=dto.scope.bom_version,
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
        row = self.repository.create(
            db,
            LlmAnalysisReportInsert(
                task_id=task.task_id,
                user_id=int(current_user.id),
                report_type=intent.requested_report_type,
                resolved_report_type=intent.resolved_report_type,
                audience=intent.audience,
                user_question=dto.user_question,
                prompt_id=dto.prompt_id,
                intent_source=intent.intent_source,
                location=dto.scope.location,
                year=dto.scope.year,
                month=dto.scope.month,
                vehicle_model=dto.scope.vehicle_model,
                bom_version=dto.scope.bom_version,
                part_number=part_number,
                stamping_supplier=dto.scope.stamping_supplier,
                engine_run_id=dto.engine_run_id,
                status=REPORT_STATUS_PENDING,
                idempotency_key=idem_key,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            ),
        )
        db.commit()

        AsyncTaskService.submit(
            self._process_in_background,
            task.task_id,
            int(row.id),
            str(audit["updated_by"]),
        )
        return self._to_task_vo(row, from_cache=False, message="正在聚合核价结果…")

    def get_report(
        self,
        db: Session,
        report_id: int,
        *,
        current_user: UserVO,
    ) -> LlmAnalysisReportVO:
        row = self.repository.get_by_id(db, report_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="报告不存在"
            )
        if int(row.user_id) != int(current_user.id) and not bool(
            getattr(current_user, "is_admin", False)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该报告"
            )
        return LlmAnalysisReportVO.from_orm_row(row)

    def list_reports(
        self,
        db: Session,
        query: LlmAnalysisReportQuery,
        *,
        current_user: UserVO,
    ) -> tuple[list[LlmAnalysisReportVO], int]:
        rows, total = self.repository.paginate(
            db,
            user_id=None if getattr(current_user, "is_admin", False) else int(current_user.id),
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
        return [LlmAnalysisReportVO.from_orm_row(row) for row in rows], total

    def get_task_progress(
        self,
        db: Session,
        task_id: str,
        *,
        current_user: UserVO,
    ) -> AsyncTaskProgressVO:
        snapshot = _async_task_service.get_task_snapshot(task_id)
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在"
            )
        row = self.repository.get_by_task_id(db, task_id)
        if row is not None and int(row.user_id) != int(current_user.id) and not bool(
            getattr(current_user, "is_admin", False)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="无权查看该任务"
            )
        result = AsyncTaskService.parse_result_json(snapshot.get("result_json"))
        return AsyncTaskProgressVO.from_snapshot(snapshot, result=result)

    def _process_in_background(
        self,
        task_id: str,
        report_id: int,
        updated_by: str,
    ) -> None:
        session_factory = DatabaseConfig.get_session_factory()
        db = session_factory()
        try:
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

            scope = AnalysisScope(
                location=row.location,
                year=row.year,
                month=row.month,
                vehicle_model=row.vehicle_model,
                bom_version=row.bom_version,
                part_number=row.part_number,
                stamping_supplier=row.stamping_supplier,
                engine_run_id=row.engine_run_id,
            )
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_RUNNING,
                progress=25,
                message="正在聚合 Context Pack…",
            )
            aggregated = self.aggregator.build(
                db,
                report_type=row.resolved_report_type,
                scope=scope,
            )
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_RUNNING,
                progress=55,
                message="正在调用模型生成报告…",
            )
            try:
                generated = self.generator.generate(
                    aggregated=aggregated,
                    user_question=row.user_question,
                    audience=row.audience,
                )
                markdown = generated.markdown_content
                llm_model = generated.llm_model
                prompt_version = generated.prompt_version
                prompt_hash = generated.prompt_hash
                prompt_tokens = generated.prompt_tokens
                completion_tokens = generated.completion_tokens
                total_tokens = generated.total_tokens
            except LlmClientError as exc:
                logger.warning("LLM 调用失败，降级规则模板: %s", exc)
                markdown = self.generator.render_fallback_markdown(
                    aggregated=aggregated,
                    user_question=row.user_question,
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
                        list(aggregated.pack_ids), ensure_ascii=False
                    ),
                    has_data=1 if aggregated.has_data else 0,
                    data_message=aggregated.data_message,
                    audit_hint=None,
                    updated_by=updated_by,
                ),
            )
            db.commit()
            _async_task_service.update_task_standalone(
                task_id,
                status=STATUS_COMPLETED,
                progress=100,
                message="分析完成",
                result={
                    "report_id": report_id,
                    "status": REPORT_STATUS_SUCCEEDED,
                    "resolved_report_type": row.resolved_report_type,
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
