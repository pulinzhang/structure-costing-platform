"""总成核价 Ready：焊接费条数与 P20 覆盖同一口径。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.costing.assembly_cost.calc.orchestrator.ready import _welding_coverage


def _coverage(
    *,
    current_ids=None,
    weld_info_count=1,
    log_status="success",
    breakdowns=None,
    fees=None,
):
    db = MagicMock()
    deps = MagicMock()
    deps.welding_fee_repo.list_by_calc_scope.return_value = fees or []
    log = None if log_status is None else SimpleNamespace(status=log_status)
    with (
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomWeldingFeeCalcLogRepository"
        ) as log_cls,
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomWeldingProcessBreakdownRepository"
        ) as bd_cls,
    ):
        log_cls.return_value.get_latest.return_value = log
        bd_cls.return_value.list_by_source_node_ids.return_value = breakdowns or []
        return _welding_coverage(
            db,
            year=2025,
            location="青岛",
            vehicle_model="T28",
            current_ids=current_ids if current_ids is not None else {10},
            weld_info_count=weld_info_count,
            welding_fee_repo=deps.welding_fee_repo,
        )


def test_welding_coverage_ignores_other_tree_and_orphan_fee_rows() -> None:
    live = SimpleNamespace(id=1, source_node_id=10)
    fees = [
        SimpleNamespace(source_breakdown_node_id=1, level=0),
        SimpleNamespace(source_breakdown_node_id=2, level=1),
        SimpleNamespace(source_breakdown_node_id=99, level=0),
    ]
    cov = _coverage(breakdowns=[live], fees=fees)

    assert cov.complete is True
    assert cov.fee_count == 1
    assert cov.level_counts == {0: 1}
    assert cov.breakdown_complete is True


def test_welding_coverage_complete_counts_only_live_fees() -> None:
    live = SimpleNamespace(id=1, source_node_id=10)
    fees = [
        SimpleNamespace(source_breakdown_node_id=1, level=0),
        SimpleNamespace(source_breakdown_node_id=99, level=1),
    ]
    cov = _coverage(breakdowns=[live], fees=fees)

    assert cov.complete is True
    assert cov.fee_count == 1
    assert cov.level_counts == {0: 1}
    assert cov.breakdown_complete is True


def test_welding_coverage_missing_fee_uses_aligned_count() -> None:
    live_a = SimpleNamespace(id=1, source_node_id=10)
    live_b = SimpleNamespace(id=2, source_node_id=10)
    fees = [SimpleNamespace(source_breakdown_node_id=1, level=0)]
    cov = _coverage(weld_info_count=2, breakdowns=[live_a, live_b], fees=fees)

    assert cov.complete is False
    assert cov.fee_count == 1
    assert "拆了 2 个，算出 1 个" in cov.message


def test_welding_coverage_failed_log_still_reports_aligned_count() -> None:
    live = SimpleNamespace(id=1, source_node_id=10)
    fees = [SimpleNamespace(source_breakdown_node_id=1, level=0)]
    cov = _coverage(log_status="failed", breakdowns=[live], fees=fees)

    assert cov.complete is False
    assert cov.fee_count == 1
    assert "最近一次是失败" in cov.message


def test_welding_coverage_expired_node_outside_current_ids_is_ignored() -> None:
    live = SimpleNamespace(id=1, source_node_id=10)
    fees = [SimpleNamespace(source_breakdown_node_id=1, level=0)]
    cov = _coverage(
        current_ids={10},
        breakdowns=[live],
        fees=fees,
    )
    assert cov.complete is True
    assert cov.breakdown_complete is True


def test_evaluate_welding_coverage_only_year_overlapping_roots() -> None:
    from app.services.costing.assembly_cost.calc.orchestrator.ready import (
        evaluate_welding_coverage,
    )

    live_root = SimpleNamespace(
        id=2,
        parent_id=None,
        level=0,
        weld_info="焊",
        seq_no=2,
        excel_row=2,
        sort_no=2,
        part_number="B",
        effective_year=2025,
        effective_month=1,
        expiry_year=None,
        expiry_month=None,
    )
    live_bd = SimpleNamespace(id=10, source_node_id=2)
    fees = [
        SimpleNamespace(source_breakdown_node_id=10, level=0),
        SimpleNamespace(source_breakdown_node_id=11, level=0),
    ]
    db = MagicMock()
    with (
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomPeriodService"
        ) as bom_cls,
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomWeldingFeeCalcLogRepository"
        ) as log_cls,
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomWeldingProcessBreakdownRepository"
        ) as bd_cls,
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomWeldingFeeRepository"
        ) as fee_cls,
    ):
        bom_svc = bom_cls.return_value
        bom_svc.list_year_overlap_trees.return_value = [live_root]
        log_cls.return_value.get_latest.return_value = SimpleNamespace(status="success")
        bd_cls.return_value.list_by_source_node_ids.return_value = [live_bd]
        fee_cls.return_value.list_by_calc_scope.return_value = fees
        cov = evaluate_welding_coverage(db, year=2025, location="青岛", vehicle_model="T28")

    assert cov.complete is True
    assert cov.fee_count == 1
    assert cov.breakdown_complete is True
    bom_svc.list_year_overlap_trees.assert_called_once_with(
        db, location="青岛", vehicle_model="T28", year=2025
    )
    bd_cls.return_value.list_by_source_node_ids.assert_called_once_with(db, [2])


def test_evaluate_welding_coverage_ignores_l1_open_expiry_under_expired_root() -> None:
    """树根已截断、L1 失效空：不得因 L1 本行漂进该年覆盖检查。"""
    from app.services.costing.assembly_cost.calc.orchestrator.ready import (
        evaluate_welding_coverage,
    )

    db = MagicMock()
    with (
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomPeriodService"
        ) as bom_cls,
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomWeldingFeeCalcLogRepository"
        ) as log_cls,
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomWeldingProcessBreakdownRepository"
        ) as bd_cls,
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomWeldingFeeRepository"
        ) as fee_cls,
    ):
        bom_svc = bom_cls.return_value
        bom_svc.list_year_overlap_trees.return_value = []
        log_cls.return_value.get_latest.return_value = SimpleNamespace(status="success")
        bd_cls.return_value.list_by_source_node_ids.return_value = []
        fee_cls.return_value.list_by_calc_scope.return_value = [
            SimpleNamespace(source_breakdown_node_id=20, level=1)
        ]
        cov = evaluate_welding_coverage(db, year=2025, location="青岛", vehicle_model="T28")

    assert cov.complete is True
    assert cov.fee_count == 0
    assert cov.breakdown_complete is True
    assert cov.message == "焊接费已完成"
    bom_svc.list_year_overlap_trees.assert_called_once_with(
        db, location="青岛", vehicle_model="T28", year=2025
    )
