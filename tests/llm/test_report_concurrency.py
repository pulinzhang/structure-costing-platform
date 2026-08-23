# -*- coding: utf-8 -*-
"""并发限流（B.7 #15）。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.schemas.dto.llm_analysis_dto import LlmAnalysisReportCreateDTO
from app.schemas.vo.user_vo import UserVO
from app.services.llm.report_service import LlmAnalysisReportService


def _user(user_id: int) -> UserVO:
    return UserVO(
        id=user_id,
        username=f"user{user_id}",
        is_active=True,
        is_admin=False,
        permissions=[],
    )


def test_create_report_rejects_when_too_many_active_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = LlmAnalysisReportService()
    db = MagicMock()
    service.repository.count_active_by_user = MagicMock(return_value=2)
    service.query_parser.parse = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        service.create_report(
            db,
            LlmAnalysisReportCreateDTO(user_question="青岛成本怎么样？"),
            current_user=_user(1),
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail == "too many requests"
