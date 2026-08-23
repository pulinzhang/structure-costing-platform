"""LLM 分析报告删除：只能删除本人的记录。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

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


def test_delete_report_owner_succeeds() -> None:
    service = LlmAnalysisReportService()
    db = MagicMock()
    row = MagicMock()
    row.user_id = 7
    service.repository.get_by_id = MagicMock(return_value=row)
    service.repository.delete_by_id = MagicMock(return_value=True)

    service.delete_report(db, 101, current_user=_user(7))

    service.repository.delete_by_id.assert_called_once_with(db, 101)
    db.commit.assert_called_once()


def test_delete_report_not_found() -> None:
    service = LlmAnalysisReportService()
    db = MagicMock()
    service.repository.get_by_id = MagicMock(return_value=None)

    with pytest.raises(HTTPException) as exc_info:
        service.delete_report(db, 999, current_user=_user(1))

    assert exc_info.value.status_code == 404
    db.commit.assert_not_called()


def test_delete_report_other_user_forbidden_even_admin() -> None:
    service = LlmAnalysisReportService()
    db = MagicMock()
    row = MagicMock()
    row.user_id = 2
    service.repository.get_by_id = MagicMock(return_value=row)

    with pytest.raises(HTTPException) as exc_info:
        service.delete_report(db, 101, current_user=_user(1, is_admin=True))

    assert exc_info.value.status_code == 403
    db.commit.assert_not_called()
