"""LLM 分析报告访问：列表/详情仅本人的记录（管理员亦然）。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.exceptions.base import NotFoundException, PermissionException
from app.schemas.dto.llm_analysis_dto import LlmAnalysisReportQuery
from app.schemas.vo.user_vo import UserVO
from app.services.llm.report_service import LlmAnalysisReportService


def _user(user_id: int, *, is_admin: bool = False) -> UserVO:
    return UserVO(
        id=user_id,
        username=f"user{user_id}",
        is_active=True,
        is_admin=is_admin,
        permissions=[],
    )


def test_list_reports_always_filters_by_current_user() -> None:
    service = LlmAnalysisReportService()
    db = MagicMock()
    service.repository.paginate = MagicMock(return_value=([], 0))

    service.list_reports(
        db,
        LlmAnalysisReportQuery(skip=0, limit=10),
        current_user=_user(7),
    )

    assert service.repository.paginate.call_args.kwargs["user_id"] == 7


def test_list_reports_admin_still_filters_by_current_user() -> None:
    service = LlmAnalysisReportService()
    db = MagicMock()
    service.repository.paginate = MagicMock(return_value=([], 0))

    service.list_reports(
        db,
        LlmAnalysisReportQuery(skip=0, limit=10),
        current_user=_user(7, is_admin=True),
    )

    assert service.repository.paginate.call_args.kwargs["user_id"] == 7


def test_get_report_owner_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    service = LlmAnalysisReportService()
    db = MagicMock()
    row = MagicMock()
    row.user_id = 3
    service.repository.get_by_id = MagicMock(return_value=row)
    expected = MagicMock()
    monkeypatch.setattr(
        "app.services.llm.report_service.LlmAnalysisReportVO.from_orm_row",
        MagicMock(return_value=expected),
    )

    report = service.get_report(db, 101, current_user=_user(3))

    assert report is expected


def test_get_report_other_user_forbidden_even_admin() -> None:
    service = LlmAnalysisReportService()
    db = MagicMock()
    row = MagicMock()
    row.user_id = 2
    service.repository.get_by_id = MagicMock(return_value=row)

    with pytest.raises(PermissionException) as exc_info:
        service.get_report(db, 101, current_user=_user(1, is_admin=True))

    assert exc_info.value.code == 403


def test_list_reports_returns_list_item_without_markdown() -> None:
    from app.schemas.vo.llm_analysis_vo import LlmAnalysisReportListItemVO

    row = MagicMock()
    row.id = 42
    row.status = "succeeded"
    row.user_question = "青岛成本怎么样？"
    row.resolved_report_type = "summary+trend"
    row.location = "青岛"
    row.year = 2026
    row.month = 8
    row.vehicle_model = "T28"
    row.bom_version = "V1"
    row.part_number = None
    row.stamping_supplier = None
    row.updated_at = None
    row.markdown_content = "# 不应出现在列表 VO"

    item = LlmAnalysisReportListItemVO.from_orm_row(row)

    assert item.report_id == 42
    assert item.user_question == "青岛成本怎么样？"
    assert "markdown" not in item.model_dump()


def test_get_task_progress_without_report_row_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = LlmAnalysisReportService()
    db = MagicMock()
    service.repository.get_by_task_id = MagicMock(return_value=None)
    monkeypatch.setattr(
        "app.services.llm.report_service._async_task_service.get_task_snapshot",
        MagicMock(return_value={"status": "running", "progress": 10}),
    )

    with pytest.raises(NotFoundException) as exc_info:
        service.get_task_progress(db, "task-abc", current_user=_user(1))

    assert exc_info.value.code == 404


def test_get_task_progress_other_user_forbidden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = LlmAnalysisReportService()
    db = MagicMock()
    row = MagicMock()
    row.user_id = 2
    service.repository.get_by_task_id = MagicMock(return_value=row)
    monkeypatch.setattr(
        "app.services.llm.report_service._async_task_service.get_task_snapshot",
        MagicMock(return_value={"status": "running", "progress": 10}),
    )

    with pytest.raises(PermissionException) as exc_info:
        service.get_task_progress(db, "task-abc", current_user=_user(1))

    assert exc_info.value.code == 403
