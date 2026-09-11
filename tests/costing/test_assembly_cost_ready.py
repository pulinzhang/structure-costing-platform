"""总成核价 Ready：焊接费条数与 P20 覆盖同一口径。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.services.costing.assembly_cost.calc.orchestrator.ready import _welding_coverage


def _coverage(
    *, current_ids=None, weld_info_count=1, log_status="success", breakdowns=None, fees=None
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
        bd_cls.return_value.list_by_scope.return_value = breakdowns or []
        return _welding_coverage(
            db,
            deps,
            year=2025,
            location="青岛",
            vehicle_model="T28",
            bom_version="D/00",
            current_ids=current_ids if current_ids is not None else {10},
            weld_info_count=weld_info_count,
        )


def test_welding_coverage_ignores_stale_and_orphan_fee_rows() -> None:
    live = SimpleNamespace(id=1, source_node_id=10)
    stale = SimpleNamespace(id=2, source_node_id=999)
    fees = [
        SimpleNamespace(source_breakdown_node_id=1, level=0),
        SimpleNamespace(source_breakdown_node_id=2, level=1),
        SimpleNamespace(source_breakdown_node_id=99, level=0),
    ]
    cov = _coverage(breakdowns=[live, stale], fees=fees)

    assert cov.complete is False
    assert cov.fee_count == 1
    assert cov.level_counts == {0: 1}
    assert "未对齐当前 BOM 树" in cov.message
    assert "对齐 1 条" in cov.message


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


def test_welding_coverage_missing_fee_uses_aligned_count() -> None:
    live_a = SimpleNamespace(id=1, source_node_id=10)
    live_b = SimpleNamespace(id=2, source_node_id=10)
    fees = [SimpleNamespace(source_breakdown_node_id=1, level=0)]
    cov = _coverage(weld_info_count=2, breakdowns=[live_a, live_b], fees=fees)

    assert cov.complete is False
    assert cov.fee_count == 1
    assert "当前树拆解 2 条，对齐 1 条" in cov.message


def test_welding_coverage_failed_log_still_reports_aligned_count() -> None:
    live = SimpleNamespace(id=1, source_node_id=10)
    fees = [SimpleNamespace(source_breakdown_node_id=1, level=0)]
    cov = _coverage(log_status="failed", breakdowns=[live], fees=fees)

    assert cov.complete is False
    assert cov.fee_count == 1
    assert "failed" in cov.message
