"""核价引擎 P0/P1 最小单测。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.vo.costing_engine_vo import CostingEngineAnnualItemVO, CostingEngineGateItemVO
from app.services.costing.engine.annual_calc_planner import AnnualCalcPlanner
from app.services.costing.engine.costing_engine_service import SOFT_UPLOAD_GATE_CODES
from app.services.costing.engine.gate_navigate import build_navigate
from app.services.costing.engine.orchestrator import RunOrchestrator
from app.services.costing.engine.progress import map_progress
from app.services.costing.engine.scope_discovery import DiscoveryResult, L0Scope, ScopeDiscovery


def _plan_item(items: list[CostingEngineAnnualItemVO], code: str) -> CostingEngineAnnualItemVO:
    return next(item for item in items if item.code == code)


def test_thickness_policy_is_hard_gate() -> None:
    assert "thickness_policy" not in SOFT_UPLOAD_GATE_CODES
    assert "packaging_transport" in SOFT_UPLOAD_GATE_CODES
    assert "vehicle_model" in SOFT_UPLOAD_GATE_CODES
    assert "vehicle_model_period" in SOFT_UPLOAD_GATE_CODES


def test_gate_navigate_hard_stop_codes_have_page() -> None:
    codes = [
        "vehicle_model",
        "vehicle_model_period",
        "stamping_process",
        "tonnage_price",
        "welding_unit_price",
        "bom_snapshot",
        "annual_part_price",
        "packaging_transport",
        "base_price",
        "thickness_policy",
        "scrap_price",
        "system_rates",
    ]
    for code in codes:
        nav = build_navigate(code, year=2025, month=1, location="青岛")
        assert nav is not None
        assert nav.page
        assert nav.label
        if code == "vehicle_model":
            assert nav.page == "stamping-parts"
            assert nav.query.get("location") == "青岛"
            assert nav.query.get("year") == 2025
            assert nav.query.get("month") == 1
            assert nav.secondary_page == "bom-structure"
        if code == "vehicle_model_period":
            assert nav.page == "vehicle-model-list"
            assert nav.query.get("location") == "青岛"
            assert nav.label == "去项目一览表"
        if code == "base_price":
            assert nav.query.get("year") == 2025
            assert nav.query.get("month") == 1
            assert nav.query.get("location") == "青岛"


def test_progress_bands_monotonic() -> None:
    assert map_progress("gate_plan", 1, 1) == 5
    assert map_progress("annual", 0, 4) == 5
    assert map_progress("steel", 1, 1) == 40
    assert map_progress("part_cost", 1, 2) == 55
    assert map_progress("assembly", 2, 4) == 82
    assert map_progress("summary", 1, 1) == 100


def test_scope_discovery_multi_bom_dedupe() -> None:
    """该月命中零件 ∪ 命中 L0；同项目多 BOM 版本均进入 L0Scope，别名重复去重。"""
    discovery = ScopeDiscovery()
    db = MagicMock()

    with (
        patch("app.services.costing.engine.scope_discovery.LocationService") as location_cls,
        patch.object(
            discovery.vehicle_model_service,
            "list_introducible",
        ) as list_introducible,
        patch.object(
            discovery.vehicle_model_service,
            "normalize",
            side_effect=lambda value: (value or "").strip() or None,
        ),
        patch.object(
            discovery.bom_snapshot_repo,
            "discover_l0_scopes",
            return_value=[
                {"location": "青岛", "vehicle_model": "T28", "bom_version": "D-00"},
                {"location": "青岛", "vehicle_model": "T28", "bom_version": "D-01"},
                {"location": "青岛基地", "vehicle_model": "T28", "bom_version": "D-00"},
            ],
        ) as discover_l0,
    ):
        location_cls.return_value.expand_for_query.return_value = ["青岛", "青岛基地"]
        list_introducible.return_value = ["T28"]
        discovery.part_repo.get_cascade_filter_options = MagicMock(
            return_value={"vehicle_models": ["T28"]}
        )
        result = discovery.discover(db, location="青岛", year=2025, month=1)

    list_introducible.assert_called_once_with(db, "青岛", 2025, 1)
    discover_l0.assert_called_once()
    assert discover_l0.call_args.kwargs["as_of_year"] == 2025
    assert discover_l0.call_args.kwargs["as_of_month"] == 1
    discovery.part_repo.get_cascade_filter_options.assert_called_once()
    cascade_kwargs = discovery.part_repo.get_cascade_filter_options.call_args.kwargs
    assert cascade_kwargs["as_of_year"] == 2025
    assert cascade_kwargs["as_of_month"] == 1
    assert result.vehicle_models == ["T28"]
    assert result.stamping_vehicle_models == ["T28"]
    assert result.as_of_vehicle_models == ["T28"]
    assert len(result.l0_scopes) == 2
    keys = {(s.vehicle_model, s.bom_version) for s in result.l0_scopes}
    assert keys == {("T28", "D-00"), ("T28", "D-01")}


def test_scope_discovery_empty_as_of_still_queries_l0() -> None:
    discovery = ScopeDiscovery()
    db = MagicMock()

    with (
        patch("app.services.costing.engine.scope_discovery.LocationService") as location_cls,
        patch.object(
            discovery.vehicle_model_service,
            "list_introducible",
        ) as list_introducible,
        patch.object(
            discovery.vehicle_model_service,
            "normalize",
            side_effect=lambda value: (value or "").strip() or None,
        ),
        patch.object(
            discovery.bom_snapshot_repo,
            "discover_l0_scopes",
            return_value=[],
        ) as discover_l0,
    ):
        location_cls.return_value.expand_for_query.return_value = ["青岛"]
        list_introducible.return_value = ["T28"]
        discovery.part_repo.get_cascade_filter_options = MagicMock(
            return_value={"vehicle_models": []}
        )
        result = discovery.discover(db, location="青岛", year=2025, month=1)

    list_introducible.assert_called_once_with(db, "青岛", 2025, 1)
    discover_l0.assert_called_once()
    assert result.vehicle_models == []
    assert result.stamping_vehicle_models == []
    assert result.as_of_vehicle_models == []
    assert result.l0_scopes == []


def test_scope_discovery_includes_l0_only_vehicle() -> None:
    discovery = ScopeDiscovery()
    db = MagicMock()

    with (
        patch("app.services.costing.engine.scope_discovery.LocationService") as location_cls,
        patch.object(
            discovery.vehicle_model_service,
            "list_introducible",
            return_value=["T28"],
        ),
        patch.object(
            discovery.vehicle_model_service,
            "normalize",
            side_effect=lambda value: (value or "").strip() or None,
        ),
        patch.object(
            discovery.bom_snapshot_repo,
            "discover_l0_scopes",
            return_value=[
                {"location": "青岛", "vehicle_model": "T28", "bom_version": "D-00"},
            ],
        ),
    ):
        location_cls.return_value.expand_for_query.return_value = ["青岛"]
        discovery.part_repo.get_cascade_filter_options = MagicMock(
            return_value={"vehicle_models": []}
        )
        result = discovery.discover(db, location="青岛", year=2026, month=7)

    assert result.vehicle_models == ["T28"]
    assert result.stamping_vehicle_models == []
    assert result.as_of_vehicle_models == ["T28"]
    assert len(result.l0_scopes) == 1


def test_scope_discovery_filters_stopped_project() -> None:
    """活件仍命中 as_of，项目该月已停 → 不进计划。"""
    discovery = ScopeDiscovery()
    db = MagicMock()

    with (
        patch("app.services.costing.engine.scope_discovery.LocationService") as location_cls,
        patch.object(
            discovery.vehicle_model_service,
            "list_introducible",
            return_value=[],
        ) as list_introducible,
        patch.object(
            discovery.vehicle_model_service,
            "normalize",
            side_effect=lambda value: (value or "").strip() or None,
        ),
        patch.object(
            discovery.bom_snapshot_repo,
            "discover_l0_scopes",
            return_value=[
                {"location": "青岛", "vehicle_model": "T28", "bom_version": "D-00"},
            ],
        ),
    ):
        location_cls.return_value.expand_for_query.return_value = ["青岛"]
        discovery.part_repo.get_cascade_filter_options = MagicMock(
            return_value={"vehicle_models": ["T28"]}
        )
        result = discovery.discover(db, location="青岛", year=2026, month=7)

    list_introducible.assert_called_once_with(db, "青岛", 2026, 7)
    assert result.as_of_vehicle_models == ["T28"]
    assert result.vehicle_models == []
    assert result.stamping_vehicle_models == []
    assert result.l0_scopes == []


def test_check_period_projects_empty_does_not_send_to_archive() -> None:
    from app.services.costing.engine.gate.stamping import check_period_projects

    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=7,
        location_aliases=["青岛"],
        vehicle_models=[],
        stamping_vehicle_models=[],
        l0_scopes=[],
    )
    item = check_period_projects(discovery, "青岛", 2026, 7)
    assert item.ok is False
    assert item.code == "vehicle_model"
    assert "可引入" not in item.message
    assert "项目一览" not in item.message
    assert item.navigate is not None
    assert item.navigate.page == "stamping-parts"


def test_check_period_projects_filtered_empty_goes_to_archive() -> None:
    from app.services.costing.engine.gate.stamping import check_period_projects

    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=7,
        location_aliases=["青岛"],
        vehicle_models=[],
        stamping_vehicle_models=[],
        l0_scopes=[],
        as_of_vehicle_models=["T28"],
    )
    item = check_period_projects(discovery, "青岛", 2026, 7)
    assert item.ok is False
    assert item.code == "vehicle_model_period"
    assert "项目一览" in item.message
    assert item.navigate is not None
    assert item.navigate.page == "vehicle-model-list"


def test_sibling_gates_skip_when_period_filtered() -> None:
    from app.services.costing.engine.gate.bom import (
        check_annual_part_price,
        check_bom_snapshot,
        check_packaging_transport,
    )
    from app.services.costing.engine.gate.item import PERIOD_FILTERED_SKIP
    from app.services.costing.engine.gate.scrap import check_scrap_price
    from app.services.costing.engine.gate.stamping import (
        check_stamping_process,
        check_tonnage_price,
    )
    from app.services.costing.engine.gate.welding import check_welding_unit_price

    filtered = DiscoveryResult(
        location="青岛",
        year=2026,
        month=7,
        location_aliases=["青岛"],
        vehicle_models=[],
        stamping_vehicle_models=[],
        l0_scopes=[],
        as_of_vehicle_models=["T28"],
    )
    repo = MagicMock()
    db = MagicMock()
    items = [
        check_stamping_process(filtered, "青岛", 2026, 7),
        check_tonnage_price(repo, db, filtered, "青岛", 2026, 7),
        check_bom_snapshot(filtered, "青岛", 2026, 7),
        check_annual_part_price(repo, db, filtered, "青岛", 2026, 7),
        check_packaging_transport(repo, db, filtered, "青岛", 2026, 7),
        check_welding_unit_price(repo, db, filtered, "青岛", 2026, 7),
        check_scrap_price(repo, db, filtered, "青岛", 2026, 7),
    ]
    assert all(item.ok and item.message == PERIOD_FILTERED_SKIP for item in items)
    assert repo.mock_calls == []

    empty = DiscoveryResult(
        location="青岛",
        year=2026,
        month=7,
        location_aliases=["青岛"],
        vehicle_models=[],
        stamping_vehicle_models=[],
        l0_scopes=[],
    )
    snapshot = check_bom_snapshot(empty, "青岛", 2026, 7)
    assert snapshot.ok is False
    assert "L0" in snapshot.message


def test_run_orchestrator_does_not_submit_nested_async_task() -> None:
    """引擎路径同进程调用子计算，禁止再 submit 子 AsyncTask。"""
    orch = RunOrchestrator()
    db = MagicMock()
    run = SimpleNamespace(id=1, status="running")
    orch.run_repo.get_by_id = MagicMock(return_value=run)
    orch.run_repo.create_step = MagicMock(
        side_effect=lambda *a, **k: SimpleNamespace(
            id=1,
            stage=k.get("stage"),
            scope_key=k.get("scope_key"),
            status=k.get("status"),
            message=k.get("message"),
        )
    )
    orch.run_repo.update_step_fields = MagicMock(side_effect=lambda db, step, **kw: step)
    orch.run_repo.update_run_fields = MagicMock(return_value=run)

    discovery = DiscoveryResult(
        location="青岛",
        year=2025,
        month=1,
        location_aliases=["青岛", "青岛基地"],
        vehicle_models=["T28"],
        stamping_vehicle_models=["T28"],
        l0_scopes=[L0Scope(location="青岛", vehicle_model="T28", bom_version="D-00")],
    )
    annual = [
        CostingEngineAnnualItemVO(
            code="annual_process_fee",
            scope_key="T28",
            exists=True,
            will_auto_calc=False,
        ),
        CostingEngineAnnualItemVO(
            code="annual_welding_breakdown",
            scope_key="T28|D-00",
            exists=True,
            will_auto_calc=False,
        ),
        CostingEngineAnnualItemVO(
            code="annual_welding_fee",
            scope_key="T28|D-00",
            exists=True,
            will_auto_calc=False,
        ),
    ]

    steel_result = SimpleNamespace(status="success", created_count=1, updated_count=0)
    part_result = SimpleNamespace(status="success")
    l0_result = SimpleNamespace(status="success")

    with patch(
        "app.services.costing.engine.orchestrator.run_orchestrator.AsyncTaskService",
        create=True,
    ) as _:
        pass

    submit_calls: list[object] = []

    def fake_submit(*args, **kwargs):
        submit_calls.append((args, kwargs))

    with (
        patch.object(orch.steel_orch, "calculate", return_value=steel_result) as steel_calc,
        patch.object(orch.part_cost_orch, "calculate", return_value=part_result),
        patch.object(orch.assembly_orch, "calculate", return_value=l0_result),
        patch(
            "app.services.async_task.async_task_service.AsyncTaskService.submit",
            side_effect=fake_submit,
        ),
        patch(
            "app.services.async_task.AsyncTaskService.submit",
            side_effect=fake_submit,
        ),
    ):
        user = SimpleNamespace(id=1, username="tester", real_name="测试", is_admin=True)
        summary = orch.execute(
            db,
            run_id=1,
            discovery=discovery,
            annual_items=annual,
            current_user=user,  # type: ignore[arg-type]
        )

    assert steel_calc.called
    assert submit_calls == []
    assert summary["status"] in ("succeeded", "partial")
    assert any(s["stage"] == "steel" for s in summary["steps"])
    assert any(s["stage"] == "assembly" for s in summary["steps"])


def test_delete_all_runs_marks_parent_tasks() -> None:
    from app.services.costing.engine.costing_engine_service import CostingEngineService

    service = CostingEngineService()
    db = MagicMock()
    service.run_repo.list_running_task_ids = MagicMock(return_value=["t-1", "t-2"])
    service.run_repo.delete_all = MagicMock(return_value=3)
    service.async_task_service.update_task_standalone = MagicMock()

    result = service.delete_all_runs(db)

    assert result.deleted_count == 3
    service.run_repo.delete_all.assert_called_once_with(db)
    assert service.async_task_service.update_task_standalone.call_count == 2


def test_delete_running_allows_new_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """删除 running 后同键不再视为进行中。"""
    from app.services.costing.engine.costing_engine_service import CostingEngineService

    service = CostingEngineService()
    db = MagicMock()

    running = SimpleNamespace(id=9, task_id="t-1", status="running")
    service.run_repo.get_by_id = MagicMock(return_value=running)
    service.run_repo.delete = MagicMock(return_value=True)
    service.async_task_service.update_task_standalone = MagicMock()

    service.delete_run(db, 9)

    service.run_repo.delete.assert_called_once_with(db, 9)
    service.async_task_service.update_task_standalone.assert_called()
    # 删除后查 running 应为空
    service.run_repo.get_running_by_key = MagicMock(return_value=None)
    assert service.run_repo.get_running_by_key(db, location="青岛", year=2025, month=1) is None


def test_gate_item_ok_false_requires_navigate_shape() -> None:
    nav = build_navigate("scrap_price", year=2025, month=2, location="青岛")
    item = CostingEngineGateItemVO(
        code="scrap_price",
        ok=False,
        missing=["无废料价"],
        message="缺少废料月度销售价",
        navigate=nav,
    )
    payload = item.model_dump(exclude_none=True)
    assert payload["ok"] is False
    assert payload["navigate"]["page"] == "scrap-price"
    assert payload["navigate"]["query"]["month"] == 2


def test_annual_planner_welding_fee_auto_calc_when_coverage_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """拆解未全覆盖时视为缺失，引擎应补算焊接费（不能只凭「有几条费行」就跳过）。"""
    from app.services.costing.assembly_cost.calc.orchestrator.ready import WeldingCoverage
    from app.services.costing.engine.scope_discovery import L0Scope
    from app.services.stamping.process_fee.calc.orchestrator.ready import ProcessFeeCoverage

    planner = AnnualCalcPlanner()
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.costing.engine.annual_calc_planner.evaluate_process_fee_coverage",
        lambda *args, **kwargs: ProcessFeeCoverage(True, "冲压加工费已完成", 1, 1),
    )
    monkeypatch.setattr(
        "app.services.costing.engine.annual_calc_planner.evaluate_welding_coverage",
        lambda *args, **kwargs: WeldingCoverage(
            False,
            "拆解节点没有对应的焊接费行（当前树拆解 86 条，对齐 9 条），请先完成焊接费计算",
            9,
            {},
        ),
    )

    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T2AA"],
        stamping_vehicle_models=["T2AA"],
        l0_scopes=[
            L0Scope(vehicle_model="T2AA", bom_version="D/00", location="青岛"),
        ],
    )
    items = planner.plan(db, discovery)
    weld = _plan_item(items, "annual_welding_fee")
    breakdown = _plan_item(items, "annual_welding_breakdown")
    assert weld.exists is False
    assert weld.will_auto_calc is True
    assert breakdown.exists is True
    assert breakdown.will_auto_calc is False


def test_annual_planner_skips_welding_fee_when_coverage_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.costing.assembly_cost.calc.orchestrator.ready import WeldingCoverage
    from app.services.costing.engine.scope_discovery import L0Scope
    from app.services.stamping.process_fee.calc.orchestrator.ready import ProcessFeeCoverage

    planner = AnnualCalcPlanner()
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.costing.engine.annual_calc_planner.evaluate_process_fee_coverage",
        lambda *args, **kwargs: ProcessFeeCoverage(True, "冲压加工费已完成", 1, 1),
    )
    monkeypatch.setattr(
        "app.services.costing.engine.annual_calc_planner.evaluate_welding_coverage",
        lambda *args, **kwargs: WeldingCoverage(True, "焊接费已完成", 86, {}),
    )

    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T2AA"],
        stamping_vehicle_models=["T2AA"],
        l0_scopes=[
            L0Scope(vehicle_model="T2AA", bom_version="D/00", location="青岛"),
        ],
    )
    items = planner.plan(db, discovery)
    weld = _plan_item(items, "annual_welding_fee")
    breakdown = _plan_item(items, "annual_welding_breakdown")
    assert weld.exists is True
    assert weld.will_auto_calc is False
    assert breakdown.exists is True
    assert breakdown.will_auto_calc is False


def test_annual_planner_process_fee_auto_calc_when_coverage_incomplete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.stamping.process_fee.calc.orchestrator.ready import ProcessFeeCoverage

    planner = AnnualCalcPlanner()
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.costing.engine.annual_calc_planner.evaluate_process_fee_coverage",
        lambda *args, **kwargs: ProcessFeeCoverage(
            False,
            "冲压零件没有对应的加工费行（工艺零件 20 条，对齐 3 条），请先完成冲压加工费计算",
            20,
            3,
        ),
    )
    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T28"],
        stamping_vehicle_models=["T28"],
        l0_scopes=[],
    )
    items = planner.plan(db, discovery)
    process_fee = _plan_item(items, "annual_process_fee")
    assert process_fee.exists is False
    assert process_fee.will_auto_calc is True


def test_annual_planner_welding_breakdown_auto_calc_when_tree_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.costing.assembly_cost.calc.orchestrator.ready import WeldingCoverage
    from app.services.costing.engine.scope_discovery import L0Scope
    from app.services.stamping.process_fee.calc.orchestrator.ready import ProcessFeeCoverage

    planner = AnnualCalcPlanner()
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.costing.engine.annual_calc_planner.evaluate_process_fee_coverage",
        lambda *args, **kwargs: ProcessFeeCoverage(True, "冲压加工费已完成", 1, 1),
    )
    monkeypatch.setattr(
        "app.services.costing.engine.annual_calc_planner.evaluate_welding_coverage",
        lambda *args, **kwargs: WeldingCoverage(
            False,
            "焊接拆解/费行未对齐当前 BOM 树（当前树对齐 9 条），请重导后重算焊接费",
            9,
            {},
            False,
        ),
    )
    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T2AA"],
        stamping_vehicle_models=[],
        l0_scopes=[
            L0Scope(vehicle_model="T2AA", bom_version="D/00", location="青岛"),
        ],
    )
    items = planner.plan(db, discovery)
    breakdown = _plan_item(items, "annual_welding_breakdown")
    weld = _plan_item(items, "annual_welding_fee")
    assert breakdown.will_auto_calc is True
    assert weld.will_auto_calc is True


def test_process_fee_coverage_requires_every_part_row() -> None:
    from app.services.stamping.process_fee.calc.orchestrator.ready import (
        evaluate_process_fee_coverage,
    )

    deps = MagicMock()
    deps.part_repo.list_by_location_and_vehicle.return_value = [
        SimpleNamespace(
            location="青岛",
            stamping_supplier="一工厂",
            version="V1",
            part_number="P001",
        ),
        SimpleNamespace(
            location="青岛",
            stamping_supplier="一工厂",
            version="V1",
            part_number="P002",
        ),
    ]
    deps.fee_repo.list_by_scope.return_value = [
        SimpleNamespace(
            location="青岛",
            stamping_supplier="一工厂",
            version="V1",
            part_number="P001",
            final_processing_fee=1,
        )
    ]
    coverage = evaluate_process_fee_coverage(
        MagicMock(),
        year=2026,
        aliases=["青岛"],
        vehicle_model="T28",
        part_repo=deps.part_repo,
        fee_repo=deps.fee_repo,
    )
    assert coverage.complete is False
    assert coverage.part_count == 2
    assert coverage.fee_count == 1


def test_annual_planner_skips_process_fee_without_stamping_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planner = AnnualCalcPlanner()
    db = MagicMock()
    coverage_fn = MagicMock()
    monkeypatch.setattr(
        "app.services.costing.engine.annual_calc_planner.evaluate_process_fee_coverage",
        coverage_fn,
    )
    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T28"],
        stamping_vehicle_models=[],
        l0_scopes=[],
    )

    items = planner.plan(db, discovery)

    assert all(item.code != "annual_process_fee" for item in items)
    coverage_fn.assert_not_called()


def test_annual_planner_skips_welding_without_bom(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.stamping.process_fee.calc.orchestrator.ready import ProcessFeeCoverage

    planner = AnnualCalcPlanner()
    db = MagicMock()
    monkeypatch.setattr(
        "app.services.costing.engine.annual_calc_planner.evaluate_process_fee_coverage",
        lambda *args, **kwargs: ProcessFeeCoverage(True, "冲压加工费已完成", 1, 1),
    )
    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T28"],
        stamping_vehicle_models=["T28"],
        l0_scopes=[],
    )

    items = planner.plan(db, discovery)

    assert any(item.code == "annual_process_fee" for item in items)
    assert all(not item.code.startswith("annual_welding") for item in items)


def test_gate_skips_tonnage_without_stamping_process() -> None:
    from app.services.costing.engine.gate_checker import GateChecker

    checker = GateChecker()
    db = MagicMock()
    checker.tonnage_repo = MagicMock()
    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T28"],
        stamping_vehicle_models=[],
        l0_scopes=[],
    )

    item = checker._check_tonnage_price(db, discovery, "青岛", 2026, 1)

    assert item.ok is True
    assert item.code == "tonnage_price"
    checker.tonnage_repo.count_by_location_year_and_statuses.assert_not_called()


def test_gate_skips_welding_unit_price_without_bom() -> None:
    from app.services.costing.engine.gate_checker import GateChecker

    checker = GateChecker()
    db = MagicMock()
    checker.welding_unit_repo = MagicMock()
    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T28"],
        stamping_vehicle_models=["T28"],
        l0_scopes=[],
    )

    item = checker._check_welding_unit_price(db, discovery, "青岛", 2026, 1)

    assert item.ok is True
    assert item.code == "welding_unit_price"
    checker.welding_unit_repo.count_by_location_year_and_statuses.assert_not_called()


def test_gate_skips_annual_part_price_without_bom() -> None:
    from app.services.costing.engine.gate_checker import GateChecker

    checker = GateChecker()
    db = MagicMock()
    checker.annual_part_repo = MagicMock()
    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T28"],
        stamping_vehicle_models=["T28"],
        l0_scopes=[],
    )

    item = checker._check_annual_part_price(db, discovery, "青岛", 2026, 1)

    assert item.ok is True
    checker.annual_part_repo.count_by_location_year_and_statuses.assert_not_called()


def test_stamping_complete_skips_without_process() -> None:
    from app.services.costing.assembly_cost.calc.orchestrator.ready import _stamping_complete

    db = MagicMock()
    with patch(
        "app.services.costing.assembly_cost.calc.orchestrator.ready.StampingPartRepository"
    ) as repo_cls:
        repo_cls.return_value.list_by_location_and_vehicle.return_value = []
        ok, suppliers, message = _stamping_complete(
            db, year=2026, month=1, location="青岛", vehicle_model="T28"
        )

    kwargs = repo_cls.return_value.list_by_location_and_vehicle.call_args.kwargs
    assert kwargs["as_of_year"] == 2026
    assert kwargs["as_of_month"] == 1

    assert ok is True
    assert suppliers == []
    assert "无冲压工艺" in message


def test_execute_assembly_runs_without_stamping_process() -> None:
    """无冲压工艺时不因加工费/零件价未做而跳过总成。"""
    from app.services.costing.engine.orchestrator.phases import PhaseCarry, execute_assembly
    from app.services.costing.engine.orchestrator.run_orchestrator import RunOrchestrator

    orch = RunOrchestrator()
    db = MagicMock()
    orch.run_repo.get_by_id = MagicMock(return_value=SimpleNamespace(id=1, status="running"))
    orch.run_repo.create_step = MagicMock(
        side_effect=lambda *a, **k: SimpleNamespace(
            id=1,
            stage=k.get("stage"),
            scope_key=k.get("scope_key"),
            status=k.get("status"),
            message=k.get("message"),
        )
    )
    orch.run_repo.update_step_fields = MagicMock(side_effect=lambda db, step, **kw: step)

    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T28"],
        stamping_vehicle_models=[],
        l0_scopes=[L0Scope(location="青岛", vehicle_model="T28", bom_version="D-00")],
    )
    carry = PhaseCarry()
    carry.failed_vehicles.add("T28")
    progress = MagicMock()
    user = SimpleNamespace(id=1, username="tester")

    with patch(
        "app.services.costing.engine.orchestrator.phases.run_assembly",
        return_value=(True, "总成核价 status=success", {"status": "success"}),
    ) as run_asm:
        execute_assembly(
            orch,
            db,
            run_id=1,
            discovery=discovery,
            current_user=user,  # type: ignore[arg-type]
            progress=progress,
            carry=carry,
        )

    assert run_asm.called
    assert any(s["status"] == "succeeded" for s in carry.step_summaries)


def test_execute_assembly_runs_once_per_vehicle_not_per_version() -> None:
    from app.services.costing.engine.orchestrator.phases import PhaseCarry, execute_assembly
    from app.services.costing.engine.orchestrator.run_orchestrator import RunOrchestrator

    orch = RunOrchestrator()
    db = MagicMock()
    orch.run_repo.get_by_id = MagicMock(return_value=SimpleNamespace(id=1, status="running"))
    orch.run_repo.create_step = MagicMock(
        side_effect=lambda *a, **k: SimpleNamespace(
            id=1,
            stage=k.get("stage"),
            scope_key=k.get("scope_key"),
            status=k.get("status"),
            message=k.get("message"),
        )
    )
    orch.run_repo.update_step_fields = MagicMock(side_effect=lambda db, step, **kw: step)
    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T28"],
        stamping_vehicle_models=[],
        l0_scopes=[
            L0Scope(location="青岛", vehicle_model="T28", bom_version="D-00"),
            L0Scope(location="青岛", vehicle_model="T28", bom_version="D-01"),
        ],
    )
    with patch(
        "app.services.costing.engine.orchestrator.phases.run_assembly",
        return_value=(True, "总成核价已完成", {"status": "success"}),
    ) as run_asm:
        execute_assembly(
            orch,
            db,
            run_id=1,
            discovery=discovery,
            current_user=SimpleNamespace(id=1, username="tester"),  # type: ignore[arg-type]
            progress=MagicMock(),
            carry=PhaseCarry(),
        )
    assert run_asm.call_count == 1


def test_calc_step_message_uses_plain_chinese() -> None:
    from app.services.costing.engine.orchestrator.runners import _calc_step_message

    assert _calc_step_message("总成核价", "success") == "总成核价已完成"
    assert "部分成功" in _calc_step_message("总成核价", "partial")
    assert _calc_step_message("零件核价", "failed") == "零件核价失败"
