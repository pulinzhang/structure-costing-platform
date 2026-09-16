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
    bom_version="D/00",
    snapshot_ids=None,
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
            year=2025,
            location="青岛",
            vehicle_model="T28",
            bom_version=bom_version,
            current_ids=current_ids if current_ids is not None else {10},
            snapshot_ids=snapshot_ids,
            weld_info_count=weld_info_count,
            welding_fee_repo=deps.welding_fee_repo,
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
    assert cov.breakdown_complete is False


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
    assert "当前树拆解 2 条，对齐 1 条" in cov.message


def test_welding_coverage_failed_log_still_reports_aligned_count() -> None:
    live = SimpleNamespace(id=1, source_node_id=10)
    fees = [SimpleNamespace(source_breakdown_node_id=1, level=0)]
    cov = _coverage(log_status="failed", breakdowns=[live], fees=fees)

    assert cov.complete is False
    assert cov.fee_count == 1
    assert "failed" in cov.message


def test_welding_coverage_without_version_ignores_other_trees() -> None:
    live = SimpleNamespace(id=1, source_node_id=10)
    other = SimpleNamespace(id=2, source_node_id=999)
    fees = [
        SimpleNamespace(source_breakdown_node_id=1, level=0),
        SimpleNamespace(source_breakdown_node_id=2, level=1),
    ]
    cov = _coverage(breakdowns=[live, other], fees=fees, bom_version=None)

    assert cov.complete is True
    assert cov.fee_count == 1
    assert cov.breakdown_complete is True


def test_welding_coverage_expired_node_in_snapshot_is_not_stale() -> None:
    live = SimpleNamespace(id=1, source_node_id=10)
    expired = SimpleNamespace(id=2, source_node_id=20)
    fees = [SimpleNamespace(source_breakdown_node_id=1, level=0)]
    cov = _coverage(
        current_ids={10},
        snapshot_ids={10, 20},
        breakdowns=[live, expired],
        fees=fees,
    )
    assert cov.complete is True
    assert cov.breakdown_complete is True


def test_evaluate_welding_coverage_only_year_overlapping_nodes() -> None:
    from app.services.costing.assembly_cost.calc.orchestrator.ready import (
        evaluate_welding_coverage,
    )

    expired = SimpleNamespace(
        id=1,
        weld_info="焊",
        effective_year=2020,
        effective_month=1,
        expiry_year=2024,
        expiry_month=12,
    )
    live = SimpleNamespace(
        id=2,
        weld_info="焊",
        effective_year=2025,
        effective_month=1,
        expiry_year=None,
        expiry_month=None,
    )
    live_bd = SimpleNamespace(id=10, source_node_id=2)
    expired_bd = SimpleNamespace(id=11, source_node_id=1)
    fees = [
        SimpleNamespace(source_breakdown_node_id=10, level=0),
        SimpleNamespace(source_breakdown_node_id=11, level=0),
    ]
    db = MagicMock()
    with (
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomSnapshotRepository"
        ) as snap_cls,
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomNodeRepository"
        ) as node_cls,
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
        snap_cls.return_value.get_by_unique_key.return_value = SimpleNamespace(id=1)
        node_cls.return_value.list_by_snapshot.return_value = [expired, live]
        log_cls.return_value.get_latest.return_value = SimpleNamespace(status="success")
        bd_cls.return_value.list_by_scope.return_value = [live_bd, expired_bd]
        fee_cls.return_value.list_by_calc_scope.return_value = fees
        cov = evaluate_welding_coverage(
            db, year=2025, location="青岛", vehicle_model="T28", bom_version="D/00"
        )

    assert cov.complete is True
    assert cov.fee_count == 1
    assert cov.breakdown_complete is True
