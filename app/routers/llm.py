"""
LLM 分析报告 API（仅后端）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.common.operation_log.context import set_request_audit_scope
from app.common.permissions.codes import Perm
from app.database import get_db
from app.deps.permissions import require_perm
from app.schemas.common.page_result import PageResult
from app.schemas.dto.llm_analysis_dto import (
    LlmAnalysisReportCreateDTO,
    LlmAnalysisReportQuery,
)
from app.schemas.vo.async_task_vo import AsyncTaskProgressVO
from app.schemas.vo.llm_analysis_vo import (
    LlmAnalysisReportListItemVO,
    LlmAnalysisReportTaskVO,
    LlmAnalysisReportVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.llm.report import LlmAnalysisReportService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/llm", tags=["AI助理"])

_service = LlmAnalysisReportService()


@router.post(
    "/reports",
    response_model=ApiResponse[LlmAnalysisReportTaskVO],
    summary="提交分析报告任务",
)
def create_report(
    dto: LlmAnalysisReportCreateDTO,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LLM_ANALYSIS_RUN)),
) -> ApiResponse[LlmAnalysisReportTaskVO]:
    set_request_audit_scope(request, {"question": dto.user_question})
    task = _service.create_report(db, dto, current_user=current_user)
    return ApiResponse.ok(data=task, message="已提交分析任务")


@router.get(
    "/reports/{report_id:int}",
    response_model=ApiResponse[LlmAnalysisReportVO],
    summary="查看分析报告",
)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LLM_ANALYSIS_VIEW)),
) -> ApiResponse[LlmAnalysisReportVO]:
    report = _service.get_report(db, report_id, current_user=current_user)
    return ApiResponse.ok(data=report)


@router.get(
    "/reports",
    response_model=ApiResponse[PageResult[LlmAnalysisReportListItemVO]],
    summary="分页查询分析报告",
)
def list_reports(
    location: str | None = Query(None),
    year: int | None = Query(None),
    month: int | None = Query(None),
    vehicle_model: str | None = Query(None),
    bom_version: str | None = Query(None),
    report_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LLM_ANALYSIS_VIEW)),
) -> ApiResponse[PageResult[LlmAnalysisReportListItemVO]]:
    query = LlmAnalysisReportQuery(
        location=location,
        year=year,
        month=month,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        report_type=report_type,
        status=status,
        page=page,
        size=size,
    )
    items, total = _service.list_reports(db, query, current_user=current_user)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=page,
        page_size=size,
    )


@router.delete(
    "/reports/{report_id:int}",
    response_model=ApiResponse[None],
    summary="删除分析报告",
)
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LLM_ANALYSIS_VIEW)),
) -> ApiResponse[None]:
    _service.delete_report(db, report_id, current_user=current_user)
    return ApiResponse.deleted(message="删除成功")


@router.get(
    "/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
    summary="查询分析报告任务进度",
)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LLM_ANALYSIS_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    progress = _service.get_task_progress(db, task_id, current_user=current_user)
    return ApiResponse.ok(data=progress)
