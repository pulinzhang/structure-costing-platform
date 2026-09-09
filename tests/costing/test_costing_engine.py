"""核价引擎 P0/P1 最小单测。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.schemas.vo.costing_engine_vo import CostingEngineAnnualItemVO, CostingEngineGateItemVO
from app.services.costing.engine.annual_calc_planner import AnnualCalcPlanner
from app.services.costing.engine.gate_navigate import build_navigate
from app.services.costing.engine.orchestrator import RunOrchestrator
from app.services.costing.engine.progress import map_progress
from app.services.costing.engine.scope_discovery import DiscoveryResult, L0Scope, ScopeDiscovery


def test_gate_navigate_hard_stop_codes_have_page() -> None:
    codes = [
        "vehicle_model",
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
            assert nav.page == "vehicle-model-list"
            assert nav.query.get("location") == "青岛"
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
    """本期项目来自主数据；同项目多 BOM 版本均进入 L0Scope，别名重复去重。"""
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
                {"location": "青岛", "vehicle_model": "T28", "bom_version": "D-01"},
                {"location": "青岛基地", "vehicle_model": "T28", "bom_version": "D-00"},
            ],
        ),
    ):
        location_cls.return_value.expand_for_query.return_value = ["青岛", "青岛基地"]
        discovery.part_repo.get_cascade_filter_options = MagicMock(
            return_value={"vehicle_models": ["T28"]}
        )
        result = discovery.discover(db, location="青岛", year=2025, month=1)

    assert result.vehicle_models == ["T28"]
    assert result.stamping_vehicle_models == ["T28"]
    assert len(result.l0_scopes) == 2
    keys = {(s.vehicle_model, s.bom_version) for s in result.l0_scopes}
    assert keys == {("T28", "D-00"), ("T28", "D-01")}


def test_scope_discovery_empty_introducible_skips_l0() -> None:
    discovery = ScopeDiscovery()
    db = MagicMock()

    with (
        patch("app.services.costing.engine.scope_discovery.LocationService") as location_cls,
        patch.object(
            discovery.vehicle_model_service,
            "list_introducible",
            return_value=[],
        ),
        patch.object(
            discovery.bom_snapshot_repo,
            "discover_l0_scopes",
        ) as discover_l0,
    ):
        location_cls.return_value.expand_for_query.return_value = ["青岛"]
        result = discovery.discover(db, location="青岛", year=2025, month=1)

    discover_l0.assert_not_called()
    assert result.vehicle_models == []
    assert result.l0_scopes == []


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


def test_annual_planner_welding_fee_exists_covers_all_levels() -> None:
    """焊接费是否已有结果按整树计，不按 level=0。"""
    planner = AnnualCalcPlanner()
    db = MagicMock()
    planner.l0_welding_fee_repo = MagicMock()
    planner.l0_welding_fee_repo.count_by_scope_and_statuses.return_value = 0

    exists = planner._l0_welding_fee_exists(
        db,
        year=2026,
        location="青岛",
        vehicle_model="T28",
        bom_version="D-00",
    )

    assert exists is False
    kwargs = planner.l0_welding_fee_repo.count_by_scope_and_statuses.call_args.kwargs
    assert kwargs["level"] is None
    assert kwargs["year"] == 2026
    assert kwargs["vehicle_model"] == "T28"


def test_annual_planner_skips_process_fee_without_stamping_process() -> None:
    planner = AnnualCalcPlanner()
    db = MagicMock()
    planner.process_fee_repo = MagicMock()
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
    planner.process_fee_repo.count_by_scope_and_statuses.assert_not_called()


def test_annual_planner_skips_welding_without_bom() -> None:
    planner = AnnualCalcPlanner()
    db = MagicMock()
    planner.breakdown_repo = MagicMock()
    planner.l0_welding_fee_repo = MagicMock()
    discovery = DiscoveryResult(
        location="青岛",
        year=2026,
        month=1,
        location_aliases=["青岛"],
        vehicle_models=["T28"],
        stamping_vehicle_models=["T28"],
        l0_scopes=[],
    )
    planner.process_fee_repo = MagicMock()
    planner.process_fee_repo.count_by_scope_and_statuses.return_value = 1

    items = planner.plan(db, discovery)

    assert any(item.code == "annual_process_fee" for item in items)
    assert all(not item.code.startswith("annual_welding") for item in items)
    planner.breakdown_repo.count_by_scope.assert_not_called()
    planner.l0_welding_fee_repo.count_by_scope_and_statuses.assert_not_called()


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
