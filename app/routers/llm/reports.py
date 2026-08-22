"""
LLM 分析报告 API（仅后端）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

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
    LlmAnalysisReportTaskVO,
    LlmAnalysisReportVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.llm.report_service import LlmAnalysisReportService
from app.utils.response import ApiResponse

router = APIRouter(prefix="/api/llm", tags=["采购智能分析"])

_service = LlmAnalysisReportService()


@router.post(
    "/reports",
    response_model=ApiResponse[LlmAnalysisReportTaskVO],
)
def create_report(
    dto: LlmAnalysisReportCreateDTO,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LLM_ANALYSIS_RUN)),
) -> ApiResponse[LlmAnalysisReportTaskVO]:
    task = _service.create_report(db, dto, current_user=current_user)
    return ApiResponse.ok(data=task, message="已提交分析任务")


@router.get(
    "/reports/{report_id}",
    response_model=ApiResponse[LlmAnalysisReportVO],
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
    response_model=ApiResponse[PageResult[LlmAnalysisReportVO]],
)
def list_reports(
    location: str | None = Query(None),
    year: int | None = Query(None),
    month: int | None = Query(None),
    vehicle_model: str | None = Query(None),
    bom_version: str | None = Query(None),
    report_type: str | None = Query(None),
    status: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LLM_ANALYSIS_VIEW)),
) -> ApiResponse[PageResult[LlmAnalysisReportVO]]:
    query = LlmAnalysisReportQuery(
        location=location,
        year=year,
        month=month,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        report_type=report_type,
        status=status,
        skip=skip,
        limit=limit,
    )
    items, total = _service.list_reports(db, query, current_user=current_user)
    return ApiResponse.list_(
        items=items,
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
    )


@router.get(
    "/tasks/{task_id}",
    response_model=ApiResponse[AsyncTaskProgressVO],
)
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: UserVO = Depends(require_perm(Perm.LLM_ANALYSIS_VIEW)),
) -> ApiResponse[AsyncTaskProgressVO]:
    progress = _service.get_task_progress(db, task_id, current_user=current_user)
    return ApiResponse.ok(data=progress)
