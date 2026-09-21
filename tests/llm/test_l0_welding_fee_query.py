"""成品焊接费问句解析与取数。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.database import DatabaseConfig
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.query.parser.pipeline import QueryParser


def test_query_parser_l0_welding_fee_subject() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛", "芜湖": "芜湖", "芜湖基地": "芜湖"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["D/00"])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2026-08"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="今年与去年，青岛基地，成品焊接费，比较。",
    )
    assert query.subject == "l0_welding_fee"
    assert query.location() == "青岛"
    assert "comparison" in query.analyses


def test_query_parser_welding_cost_anomaly_routes_to_fee() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T13J"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["D/00"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-01"},
            "filters": {},
            "compare_locations": [],
        }
    )
    query = parser.parse(
        db,
        user_question="2026年01月焊接成本计算异常",
    )
    assert query.query_mode == "analysis"
    assert query.subject == "l0_welding_fee"
    assert "risk" in query.analyses


def test_build_welding_fee_mom_anomalies_requires_ten_percent() -> None:
    from decimal import Decimal

    from app.repositories.llm.l0_welding_fee_analysis_repository import L0WeldingFeeRow
    from app.services.llm.analysis.shared.cost_driver import build_welding_fee_mom_anomalies

    def row(year: int, fee: Decimal) -> L0WeldingFeeRow:
        return L0WeldingFeeRow(
            year=year,
            location="青岛",
            vehicle_model="T13J",
            bom_version="D/00",
            part_number="W001",
            part_name="焊件",
            total_l0_welding_fee=fee,
            other_fee=None,
            final_l0_welding_fee=fee,
            calc_status="ok",
            audit_status="approved",
        )

    under = [row(2025, Decimal("100")), row(2026, Decimal("109"))]
    over = [row(2025, Decimal("100")), row(2026, Decimal("110"))]
    assert build_welding_fee_mom_anomalies(under, focus_year=2026)["items"] == []
    over_result = build_welding_fee_mom_anomalies(over, focus_year=2026)
    assert len(over_result["items"]) == 1
    assert over_result["items"][0]["change_rate"] == "0.10"


@pytest.mark.integration
def test_l0_welding_fee_qingdao_yoy() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        from sqlalchemy import inspect as sa_inspect

        if "bom_welding_fees" not in set(sa_inspect(db.get_bind()).get_table_names()):
            pytest.skip("bom_welding_fees 尚未迁移")
        query = QueryParser().parse(
            db,
            user_question="今年与去年，青岛基地，成品焊接费，比较。",
        )
        assert query.subject == "l0_welding_fee"

        run = AnalysisRunner().run(db, query)
        if not run.has_data:
            pytest.skip("青岛成品焊接费当前库无数据")
        assert run.has_data is True
        assert run.summary is not None
        assert run.summary["row_count"] > 0
        assert len(run.summary["years"]) >= 2
    finally:
        db.close()
