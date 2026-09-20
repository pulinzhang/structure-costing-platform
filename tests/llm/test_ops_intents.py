"""管理者作业台 / 模具检具 / 采购对象：分流与 summary。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.repositories.llm.ops_workbench_repository import WorkbenchBoardRow
from app.repositories.llm.procurement_object_analysis_repository import ProcurementObjectRow
from app.services.llm.analysis.ops.masterdata import build_procurement_object_summary
from app.services.llm.analysis.ops.workbench import (
    build_ops_workbench_risks,
    build_ops_workbench_summary,
)
from app.services.llm.query.intent_router import (
    detect_audience,
    detect_help_topic,
    detect_query_mode,
)
from app.services.llm.query.parser.subjects import resolve_subject
from app.services.llm.query.query_parser import QueryParser


@pytest.mark.parametrize(
    ("question", "expected_mode"),
    [
        ("青岛当月待审核还有多少", "analysis"),
        ("核价进度怎么样", "analysis"),
        ("采购对象还有多少没确认外发", "analysis"),
        ("今年模具费待审核有多少", "analysis"),
        ("检具费情况怎么样", "analysis"),
        ("2025年，T13J项目采购对象的费用是多少", "usage_help"),
        ("哪一个采购对象没有供应商", "analysis"),
        ("哪些采购对象没有供应商", "analysis"),
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
        ("芜湖T13J外发件缺供应商的有多少", "procurement_object"),
        ("哪一个采购对象没有供应商", "procurement_object"),
        ("哪些采购对象没有供应商", "procurement_object"),
        ("2856是外发还是自制", "procurement_object"),
        ("2026年01月 T13J 项目总成核价有没有异常", "l0"),
    ],
)
def test_ops_subject_resolution(question: str, expected_subject: str) -> None:
    assert resolve_subject(question=question, analyses=["summary"], filters={}) == expected_subject


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


def test_procurement_object_missing_supplier_items() -> None:
    rows = [
        ProcurementObjectRow(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/09",
            part_number="P-OUT-1",
            part_name="外发缺供应商",
            section="object",
            object_kind="stamping",
            confirm_status="outsourced",
            audit_status="pending",
            supplier_name=None,
        ),
        ProcurementObjectRow(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/09",
            part_number="P-OUT-2",
            part_name="外发已指定",
            section="object",
            object_kind="stamping",
            confirm_status="outsourced",
            audit_status="pending",
            supplier_name="某二级厂",
        ),
        ProcurementObjectRow(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/09",
            part_number="P-IN",
            part_name="自制无供应商正常",
            section="object",
            object_kind="stamping",
            confirm_status="in_house",
            audit_status="pending",
            supplier_name=None,
        ),
    ]
    summary = build_procurement_object_summary(rows)
    assert summary["missing_supplier_count"] == 1
    items = summary["missing_supplier_items"]
    assert isinstance(items, list) and len(items) == 1
    assert items[0]["part_number"] == "P-OUT-1"


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
        ("哪一个采购对象没有供应商", None, "buyer"),
        ("当月核算情况怎么样", None, "buyer_lead"),
    ],
)
def test_detect_audience(question: str, explicit: str | None, expected: str) -> None:
    assert detect_audience(question, explicit) == expected
