"""标准件问价：核价表材料行优先，年度零件价兜底。"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.repositories.llm.annual_part_price_analysis_repository import AnnualPartPriceRow
from app.repositories.llm.cost_analysis.rows import L0CompositionLineRow
from app.schemas.llm.analysis_query import AnalysisQuery, TimeRange
from app.services.llm.analysis.assembly.run import AssemblyAnalysis
from app.services.llm.analysis.runner import AnalysisRunner
from app.services.llm.analysis.shared.drilldown import (
    build_annual_leaf_price,
    build_item_price_drilldown,
    build_missing_part_price,
)
from app.services.llm.query.parser.pipeline import QueryParser


def _item_row(
    *,
    unit_price: str = "18.6800",
    parent: str = "502008023AA",
) -> L0CompositionLineRow:
    price = Decimal(unit_price)
    return L0CompositionLineRow(
        year=2026,
        month=1,
        root_part_number=parent,
        root_part_name="测试总成",
        root_should_cost=Decimal("100"),
        child_part_number="FQ199D0616T25F19N",
        child_part_name="盘头焊接螺栓",
        cost_source="annual",
        unit_price=price,
        effective_qty=Decimal("4"),
        line_amount=price * 4,
        supply_type="buy",
        location="芜湖",
    )


def test_build_item_price_from_costing_table() -> None:
    payload = build_item_price_drilldown(
        [
            _item_row(parent="502008023AA"),
            _item_row(parent="502008026AA"),
        ],
        part_token="FQ199D0616T25F19N",
    )
    assert payload["found"] is True
    assert payload["fork"] == "material_line"
    assert payload["price_source_label"] == "核价表"
    assert payload["unit_price"] == "18.68"
    assert payload["year"] == 2026
    assert payload["month"] == 1
    assert {row["part_number"] for row in payload["parents"]} == {
        "502008023AA",
        "502008026AA",
    }


def test_build_annual_leaf_price_states_fallback() -> None:
    payload = build_annual_leaf_price(
        AnnualPartPriceRow(
            year=2026,
            location="芜湖",
            part_number="FQ199D0616T25F19N",
            part_name="盘头焊接螺栓",
            unit="pcs",
            unit_price=Decimal("18.6800"),
            supply_type="标准件",
            audit_status="approved",
        ),
        part_token="FQ199D0616T25F19N",
    )
    assert payload["fork"] == "annual_price"
    assert payload["price_source_label"] == "年度零件价列表"
    assert payload["unit_price"] == "18.68"
    assert payload["looked_in"] == ["核价表", "年度零件价列表"]


def test_build_missing_part_price() -> None:
    payload = build_missing_part_price("NO-SUCH-PART")
    assert payload["found"] is False
    assert payload["fork"] == "missing"
    assert "不存在" in payload["message"]


def _mock_aligner(parser: QueryParser) -> None:
    parser._aligner._scope_repo.list_locations = MagicMock(return_value=["芜湖"])
    parser._aligner._scope_repo.location_alias_map = MagicMock(
        return_value={"芜湖": "芜湖", "芜湖基地": "芜湖"}
    )
    parser._aligner._scope_repo.list_vehicle_models = MagicMock(return_value=["T13J"])
    parser._aligner._scope_repo.list_bom_versions = MagicMock(return_value=["D/09"])
    parser._aligner._scope_repo.list_part_numbers_matching = MagicMock(return_value=[])


def test_query_parser_standard_part_price_is_how_much() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
        return_value={"time_range": {"start": "2026-09", "end": "2026-09"}, "filters": {}}
    )
    parser._cost_repo.query_latest_card_scope = MagicMock(
        return_value=SimpleNamespace(
            year=2026,
            month=1,
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/09",
            part_number="502008023AA",
            is_tree_root=True,
            object_kind="l0",
            root_part_number="502008023AA",
        )
    )
    query = parser.parse(db, user_question="FQ199D0616T25F19N零件价格是多少？")
    assert query.part_number() == "FQ199D0616T25F19N"
    assert query.analyses == ["drilldown"]
    assert query.subject == "l0"
    assert query.asks_part_price is True
    assert query.time_range.start == "2026-01"
    assert query.time_range.end == "2026-01"


def test_query_parser_bare_part_price_phrase() -> None:
    parser = QueryParser()
    db = MagicMock()
    _mock_aligner(parser)
    parser._extractor.extract = MagicMock(
        return_value={"time_range": {"start": "2026-09", "end": "2026-09"}, "filters": {}}
    )
    parser._cost_repo.query_latest_card_scope = MagicMock(
        return_value=SimpleNamespace(
            year=2026,
            month=1,
            location="芜湖",
            vehicle_model="T13J",
            bom_version="D/09",
            part_number="551001137AA",
            is_tree_root=False,
            object_kind="l1",
            root_part_number="551002784AA",
        )
    )
    query = parser.parse(db, user_question="551001137AA零件价格")
    assert query.part_number() == "551001137AA"
    assert query.analyses == ["drilldown"]
    assert query.subject == "l0"
    assert query.asks_part_price is True
    assert "summary" not in query.analyses


def test_runner_prefers_costing_item_over_annual() -> None:
    runner = AssemblyAnalysis()
    runner._l0_repo.query_part_rows = MagicMock(return_value=[])
    runner._l0_repo.query_item_price_rows = MagicMock(
        return_value=[_item_row(), _item_row(parent="502008026AA")]
    )
    runner._annual_part_price_repo.query_rows = MagicMock(
        return_value=[
            AnnualPartPriceRow(
                year=2026,
                location="芜湖",
                part_number="FQ199D0616T25F19N",
                part_name="盘头焊接螺栓",
                unit="pcs",
                unit_price=Decimal("99.0000"),
                supply_type="标准件",
                audit_status="approved",
            )
        ]
    )
    query = AnalysisQuery(
        time_range=TimeRange(start="2026-01", end="2026-01"),
        filters={"part_number": "FQ199D0616T25F19N", "location": "芜湖"},
        subject="l0",
        analyses=["drilldown"],
        user_question="FQ199D0616T25F19N零件价格是多少？",
    )
    result = runner.run_part_price_drilldown(MagicMock(), query)
    assert result.has_data is True
    assert result.result["price_source_label"] == "核价表"
    assert result.result["unit_price"] == "18.68"
    runner._annual_part_price_repo.query_rows.assert_not_called()


def test_runner_falls_back_to_annual_when_costing_empty() -> None:
    runner = AssemblyAnalysis()
    runner._l0_repo.query_part_rows = MagicMock(return_value=[])
    runner._l0_repo.query_item_price_rows = MagicMock(return_value=[])
    runner._annual_part_price_repo.query_rows = MagicMock(
        return_value=[
            AnnualPartPriceRow(
                year=2026,
                location="芜湖",
                part_number="FQ199D0616T25F19N",
                part_name="盘头焊接螺栓",
                unit="pcs",
                unit_price=Decimal("18.6800"),
                supply_type="标准件",
                audit_status="approved",
            )
        ]
    )
    runner._annual_part_price_repo.pick_best_row = MagicMock(
        side_effect=lambda rows, part_token: rows[0] if rows else None
    )
    query = AnalysisQuery(
        time_range=TimeRange(start="2026-01", end="2026-01"),
        filters={"part_number": "FQ199D0616T25F19N"},
        subject="l0",
        analyses=["drilldown"],
        user_question="FQ199D0616T25F19N零件价格是多少？",
    )
    result = runner.run_part_price_drilldown(MagicMock(), query)
    assert result.result["price_source_label"] == "年度零件价列表"
    assert result.result["unit_price"] == "18.68"


def test_runner_missing_part() -> None:
    runner = AssemblyAnalysis()
    runner._l0_repo.query_part_rows = MagicMock(return_value=[])
    runner._l0_repo.query_item_price_rows = MagicMock(return_value=[])
    runner._annual_part_price_repo.query_rows = MagicMock(return_value=[])
    runner._annual_part_price_repo.pick_best_row = MagicMock(return_value=None)
    query = AnalysisQuery(
        time_range=TimeRange(start="2026-01", end="2026-01"),
        filters={"part_number": "NO-SUCH-PART"},
        subject="l0",
        analyses=["drilldown"],
        user_question="NO-SUCH-PART零件价格是多少？",
    )
    result = runner.run_part_price_drilldown(MagicMock(), query)
    assert result.has_data is False
    assert result.result["found"] is False


def test_runner_part_subject_bare_price_uses_item_fallback() -> None:
    runner = AnalysisRunner()
    runner._assembly._l0_repo.query_part_rows = MagicMock(return_value=[])
    runner._assembly._l0_repo.query_item_price_rows = MagicMock(
        return_value=[
            L0CompositionLineRow(
                year=2026,
                month=1,
                root_part_number="551002784AA",
                root_part_name="左后门上铰链加强板总成",
                root_should_cost=Decimal("41.24"),
                child_part_number="551001137AA",
                child_part_name="左后门上铰链安装板总成",
                cost_source="assembly",
                unit_price=Decimal("29.5236"),
                effective_qty=Decimal("1"),
                line_amount=Decimal("29.5236"),
                supply_type="make",
                location="芜湖",
            )
        ]
    )
    runner._assembly._annual_part_price_repo.query_rows = MagicMock(return_value=[])
    query = AnalysisQuery(
        time_range=TimeRange(start="2026-09", end="2026-09"),
        filters={"part_number": "551001137AA"},
        subject="part",
        analyses=["summary", "drilldown"],
        asks_part_price=True,
        user_question="551001137AA零件价格",
    )
    result = runner.run(MagicMock(), query)
    assert result.has_data is True
    assert result.result["found"] is True
    assert result.result["unit_price"] == "29.52"
