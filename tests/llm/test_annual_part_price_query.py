"""年度零件价 / 一口价 问句解析与取数。"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.database import DatabaseConfig
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.query.query_parser import QueryParser


def test_query_parser_annual_part_price_subject() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛", "芜湖"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛", "芜湖": "芜湖", "芜湖基地": "芜湖"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T28"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["V3"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2025-01", "end": "2026-08"},
            "filters": {"location": "青岛基地"},
            "compare_locations": [],
        }
    )

    query = parser.parse(
        db,
        user_question="今年与去年，青岛基地，年度零件价，比较。",
    )
    assert query.subject == "annual_part_price"
    assert query.location() == "青岛"
    assert "comparison" in query.analyses


def test_query_parser_yikoujia_alias() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["青岛"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"青岛": "青岛", "青岛基地": "青岛", "芜湖": "芜湖", "芜湖基地": "芜湖"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=[])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=[])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=["501004437AA"])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-08"},
            "filters": {"location": "青岛", "part_number": "4437"},
            "compare_locations": [],
        }
    )

    query = parser.parse(db, user_question="青岛，4437，一口价多少")
    assert query.subject == "annual_part_price"
    assert query.part_number() == "501004437AA"
    assert "drilldown" in query.analyses


def _price_row(**kwargs):
    from decimal import Decimal

    from app.repositories.llm.annual_part_price_analysis_repository import AnnualPartPriceRow

    values = {
        "year": 2026,
        "location": "芜湖",
        "part_number": "B11-4102613",
        "part_name": "点焊胶",
        "unit": "mm",
        "unit_price": Decimal("8.8800"),
        "supply_type": "胶块",
        "audit_status": "pending",
        "purchase_unit": "桶",
        "purchase_unit_price": Decimal("8.8800"),
        "conversion_factor": Decimal("10000"),
    }
    values.update(kwargs)
    return AnnualPartPriceRow(**values)


def test_glue_skipped_conversion_is_flagged() -> None:
    from app.services.llm.analysis.bom.annual_part_price import (
        build_annual_part_price_conversion_anomalies,
    )

    result = build_annual_part_price_conversion_anomalies([_price_row()])
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["anomaly_type"] == "skipped_conversion"
    assert item["part_number"] == "B11-4102613"
    assert item["expected_unit_price"] == "0.0009"
    assert item["unit_price"] == "8.8800"


def test_correct_mm_unit_price_not_flagged() -> None:
    from decimal import Decimal

    from app.services.llm.analysis.bom.annual_part_price import (
        build_annual_part_price_conversion_anomalies,
    )

    result = build_annual_part_price_conversion_anomalies(
        [_price_row(unit_price=Decimal("0.0009"))]
    )
    assert result["items"] == []


def test_query_parser_annual_price_anomaly_includes_risk() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["芜湖"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"芜湖": "芜湖", "芜湖基地": "芜湖"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=[])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=[])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-12"},
            "filters": {"location": "芜湖"},
            "compare_locations": [],
        }
    )
    query = parser.parse(db, user_question="芜湖，2026年，年度零件价有无异常")
    assert query.subject == "annual_part_price"
    assert "risk" in query.analyses
    query_bundle = parser.parse(db, user_question="芜湖一口价有没有异常")
    assert query_bundle.subject == "annual_part_price"
    assert "risk" in query_bundle.analyses


def test_query_parser_standard_part_price_anomaly_routes_to_annual() -> None:
    parser = QueryParser()
    db = MagicMock()
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["芜湖"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"芜湖": "芜湖", "芜湖基地": "芜湖"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=[])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=[])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-01"},
            "filters": {"location": "芜湖"},
            "compare_locations": [],
        }
    )
    query = parser.parse(db, user_question="芜湖，标准件价格有无异常？")
    assert query.subject == "annual_part_price"
    assert "risk" in query.analyses


def test_standard_part_high_piece_price_is_flagged() -> None:
    from decimal import Decimal

    from app.services.llm.analysis.shared.standard_part_price import (
        build_standard_part_price_anomalies,
        standard_part_price_risk_entry,
    )

    cheap = _price_row(
        part_number="N0111931",
        part_name="焊接方螺母",
        unit="pcs",
        unit_price=Decimal("0.0420"),
        supply_type="标准件",
        purchase_unit="pcs",
        purchase_unit_price=Decimal("0.0420"),
        conversion_factor=Decimal("1"),
    )
    expensive = _price_row(
        part_number="Q1980616",
        part_name="承面凸焊螺栓",
        unit="pcs",
        unit_price=Decimal("8.8800"),
        supply_type="标准件",
        purchase_unit="pcs",
        purchase_unit_price=Decimal("8.8800"),
        conversion_factor=Decimal("1"),
    )
    glue_mm = _price_row()
    result = build_standard_part_price_anomalies([cheap, expensive, glue_mm])
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["anomaly_type"] == "standard_part_high_price"
    assert item["part_number"] == "Q1980616"
    assert item["unit_price"] == "8.8800"
    risk = standard_part_price_risk_entry(result)
    assert risk is not None
    assert risk["risk_type"] == "standard_part_high_price"


@pytest.mark.integration
def test_annual_part_price_qingdao_yoy() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        parser = QueryParser()
        parser._extractor.extract = MagicMock(
            return_value={
                "time_range": {"start": "2025-01", "end": "2025-12"},
                "filters": {"location": "青岛基地"},
                "compare_locations": [],
            }
        )
        query = parser.parse(
            db,
            user_question="今年与去年，青岛基地，年度零件价，比较。",
        )
        assert query.subject == "annual_part_price"

        run = AnalysisRunner().run(db, query)
        assert run.has_data is True
        assert run.summary is not None
        assert run.summary["row_count"] == 45
        assert run.summary["years"] == [2025]

        result = run.result
        if result.get("kind") == "composite":
            comparison = (result.get("parts") or {}).get("comparison") or {}
        else:
            comparison = result
        assert comparison.get("location") == "青岛"
        assert comparison.get("part_count") == 45
    finally:
        db.close()


@pytest.mark.integration
def test_annual_part_price_yikoujia_drilldown() -> None:
    db = DatabaseConfig.get_session_factory()()
    try:
        query = QueryParser().parse(db, user_question="青岛，4437，一口价多少")
        assert query.subject == "annual_part_price"

        run = AnalysisRunner().run(db, query)
        assert run.has_data is True

        result = run.result
        if result.get("kind") == "composite":
            drill = (result.get("parts") or {}).get("drilldown") or {}
        else:
            drill = result
        assert drill.get("found") is True
        assert drill.get("part_number") == "501004437AA"
        assert drill.get("unit_price") == "2.1300"
    finally:
        db.close()
