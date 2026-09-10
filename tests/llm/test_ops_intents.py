"""管理者作业台 / 模具检具 / 采购对象：分流与 summary。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.repositories.llm.ops_workbench_repository import WorkbenchBoardRow
from app.services.llm.analysis.ops_workbench import (
    build_ops_workbench_risks,
    build_ops_workbench_summary,
)
from app.services.llm.query.intent_router import (
    detect_audience,
    detect_help_topic,
    detect_query_mode,
)
from app.services.llm.query.query_parser import QueryParser


@pytest.mark.parametrize(
    ("question", "expected_mode"),
    [
        ("青岛当月待审核还有多少", "analysis"),
        ("核价进度怎么样", "analysis"),
        ("采购对象还有多少没确认外发", "analysis"),
        ("今年模具费待审核有多少", "analysis"),
        ("检具费情况怎么样", "analysis"),
        ("总成核价怎么审核", "usage_help"),
        ("冲压零件价格计算页在哪", "usage_help"),
        ("模具费怎么算进零件价", "usage_help"),
    ],
)
def test_ops_query_mode(question: str, expected_mode: str) -> None:
    assert detect_query_mode(question) == expected_mode


@pytest.mark.parametrize(
    ("question", "expected_topic"),
    [
        ("总成核价怎么审核", "audit"),
        ("怎么反审核", "audit"),
        ("冲压零件价格计算页在哪", "calc_run"),
        ("模具费计算怎么进", "calc_run"),
    ],
)
def test_ops_help_topic(question: str, expected_topic: str) -> None:
    assert detect_help_topic(question) == expected_topic


@pytest.mark.parametrize(
    ("question", "expected_subject"),
    [
        ("青岛当月待审核还有多少", "ops_workbench"),
        ("T13J 核价进度怎么样", "ops_workbench"),
        ("今年模具费待审核有多少", "stamping_die_fee"),
        ("青岛检具费情况怎么样", "stamping_gauge_fee"),
        ("采购对象还有多少没确认外发", "procurement_object"),
        ("2026年01月 T13J 项目总成核价有没有异常", "l0"),
    ],
)
def test_ops_subject_resolution(question: str, expected_subject: str) -> None:
    parser = QueryParser()
    assert (
        parser._resolve_subject(question=question, analyses=["summary"], filters={})
        == expected_subject
    )


def test_query_parser_workbench_includes_risk() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V1"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-01"},
            "filters": {"location": "青岛"},
            "compare_locations": [],
        }
    )
    query = parser.parse(db, user_question="青岛 2026年01月待审核还有多少")
    assert query.query_mode == "analysis"
    assert query.subject == "ops_workbench"
    assert "risk" in query.analyses


def test_ops_workbench_summary_totals() -> None:
    boards = [
        WorkbenchBoardRow(
            slice_id="assembly",
            label="总成核价",
            hash_page="assembly-cost",
            grain="month",
            row_count=10,
            pending_audit_count=3,
            incomplete_count=1,
        ),
        WorkbenchBoardRow(
            slice_id="procurement",
            label="采购对象",
            hash_page="bom-procurement-object-list",
            grain="list",
            row_count=8,
            pending_audit_count=1,
            incomplete_count=2,
            pending_confirm_count=4,
        ),
    ]
    summary = build_ops_workbench_summary(boards)
    assert summary["pending_audit_total"] == 4
    assert summary["incomplete_total"] == 3
    assert summary["pending_confirm_total"] == 4
    risks = build_ops_workbench_risks(summary)
    types = {item["risk_type"] for item in risks["risks"]}
    assert types == {"pending_audit", "calc_incomplete", "pending_confirm"}


@pytest.mark.parametrize(
    ("question", "explicit", "expected"),
    [
        ("当月待审核还有多少", None, "buyer_lead"),
        ("总成核价怎么审核", None, "buyer"),
        ("当月核算情况怎么样", "buyer", "buyer"),
        ("冲压零件价格计算页在哪", None, "buyer"),
        ("2856的价格多少？", None, "buyer"),
        ("8898在不在库里", None, "buyer"),
        ("当月核算情况怎么样", None, "buyer_lead"),
    ],
)
def test_detect_audience(question: str, explicit: str | None, expected: str) -> None:
    assert detect_audience(question, explicit) == expected
