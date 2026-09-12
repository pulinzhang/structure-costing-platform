"""总成材料构成独大异常。"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from app.repositories.llm.cost_analysis_repository import L0CompositionLineRow
from app.services.llm.analysis.shared.composition import (
    build_composition_anomalies,
    composition_risk_entry,
)
from app.services.llm.query.query_parser import QueryParser
from tests.llm.test_query_parser import _mock_aligner


def _line(
    *,
    child: str = "B11-4102613",
    child_name: str = "点焊胶",
    should_cost: str = "2913.9329",
    line_amount: str = "2687.3145",
    unit_price: str = "0.0009",
    qty: str = "2985905",
    source: str = "annual",
) -> L0CompositionLineRow:
    return L0CompositionLineRow(
        year=2026,
        month=1,
        root_part_number="502007416AA",
        root_part_name="右侧围内板前部总成",
        root_should_cost=Decimal(should_cost),
        child_part_number=child,
        child_part_name=child_name,
        cost_source=source,
        unit_price=Decimal(unit_price),
        effective_qty=Decimal(qty),
        line_amount=Decimal(line_amount),
    )


def test_glue_line_flags_composition_dominance() -> None:
    result = build_composition_anomalies([_line()])
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["anomaly_type"] == "composition_dominance"
    assert item["child_part_number"] == "B11-4102613"
    assert item["cost_source_label"] == "外购件"
    assert item["unit_price"] == "0.0009"
    assert Decimal(item["share_of_should_cost"]) >= Decimal("0.50")
    risk = composition_risk_entry(result)
    assert risk is not None
    assert risk["risk_type"] == "composition_dominance"


def test_normal_purchased_share_not_flagged() -> None:
    result = build_composition_anomalies(
        [
            _line(
                child="504000631AA",
                child_name="隔音胶块",
                line_amount="15.3507",
                unit_price="15.3507",
                qty="1",
            )
        ]
    )
    assert result["items"] == []
    assert composition_risk_entry(result) is None


def test_extreme_qty_flags_below_half_share() -> None:
    result = build_composition_anomalies(
        [
            _line(
                should_cost="10000",
                line_amount="2500",
                unit_price="0.0009",
                qty="10000",
            )
        ]
    )
    assert len(result["items"]) == 1
    assert result["items"][0]["anomaly_type"] == "extreme_qty"


def test_query_parser_generic_costing_anomaly_routes_to_l0() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
        return_value={
            "time_range": {"start": "2026-01", "end": "2026-01"},
            "filters": {},
            "compare_locations": [],
        }
    )
    query = parser.parse(db, user_question="2026年01月，核价有无异常")
    assert query.query_mode == "analysis"
    assert query.subject == "l0"
    assert "risk" in query.analyses


def test_standard_part_line_high_price_is_flagged() -> None:
    from app.services.llm.analysis.shared.standard_part_price import (
        build_standard_part_price_anomalies,
    )

    result = build_standard_part_price_anomalies(
        [
            _line(
                child="Q1980616",
                child_name="承面凸焊螺栓",
                line_amount="8.8800",
                unit_price="8.8800",
                qty="1",
            )
        ]
    )
    assert len(result["items"]) == 1
    assert result["items"][0]["anomaly_type"] == "standard_part_high_price"
    assert result["items"][0]["part_number"] == "Q1980616"


def test_cheap_nut_not_flagged_as_standard_part_price() -> None:
    from app.services.llm.analysis.shared.standard_part_price import (
        build_standard_part_price_anomalies,
    )

    result = build_standard_part_price_anomalies(
        [
            _line(
                child="N0111931",
                child_name="焊接方螺母",
                line_amount="0.0840",
                unit_price="0.0420",
                qty="2",
            )
        ]
    )
    assert result["items"] == []
