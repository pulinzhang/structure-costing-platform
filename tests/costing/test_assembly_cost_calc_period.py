"""总成核价计算：按 BOM 节点有效期命中计算月，不靠版本。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.exceptions.base import BusinessException
from app.schemas.dto.assembly_cost_dto import AssemblyCostCalcDTO
from app.services.costing.assembly_cost.calc.orchestrator.prep import prepare_calc_run
from app.services.costing.assembly_cost.calc.orchestrator.progress import ProgressNotifier
from app.services.costing.assembly_cost.calc.orchestrator.ready import collect_calc_ready


def _ready() -> SimpleNamespace:
    return SimpleNamespace(ready=True, message=None)


def _dto() -> AssemblyCostCalcDTO:
    return AssemblyCostCalcDTO(
        year=2026,
        month=7,
        location="青岛",
        vehicle_model="T13J",
        bom_version="D/09",
    )


@patch("app.services.costing.assembly_cost.calc.orchestrator.prep.VehicleModelService")
@patch(
    "app.services.costing.assembly_cost.calc.orchestrator.prep.assert_calc_ready",
    return_value=_ready(),
)
def test_prep_lists_as_of_trees_without_version(
    _ready_mock: MagicMock,
    vehicle_cls: MagicMock,
) -> None:
    vehicle_cls.return_value.require_introducible.return_value = ("青岛", "T13J")
    deps = MagicMock()
    node = SimpleNamespace(
        id=1,
        parent_id=None,
        level=0,
        part_number="501",
        part_name="总成",
        qty=None,
        node_role="assembly",
        sort_no=1,
        seq_no=1,
        supply_type=None,
        sketch_url=None,
        snapshot_id=9,
        bom_version="D/09",
        weld_info=None,
    )
    deps.bom_node_repo.list_as_of_trees.return_value = [node]
    deps.stamping_cost_repo.list_calc_success_with_unit_cost.return_value = []
    deps.annual_price_repo.list_with_unit_price.return_value = []
    deps.welding_fee_repo.list_by_calc_scope.return_value = []
    deps.packaging_fee_repo.list_by_location_year.return_value = []
    deps.settings_service.get_finished_finance_rate.return_value = 0
    deps.settings_service.get_finished_management_rate.return_value = 0
    deps.settings_service.get_finished_scrap_rate.return_value = 0
    deps.settings_service.get_finished_pretax_profit_rate.return_value = 0

    with (
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.prep.BomProcurementObjectRepository"
        ) as proc_cls,
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.prep.BomWeldingProcessBreakdownRepository"
        ) as bd_cls,
    ):
        proc_cls.return_value.list_lists_by_location_vehicle.return_value = []
        proc_cls.return_value.list_objects_by_list_id.return_value = []
        bd_cls.return_value.list_by_scope.return_value = []
        prepare_calc_run(MagicMock(), deps, _dto(), ProgressNotifier())

    kwargs = deps.bom_node_repo.list_as_of_trees.call_args.kwargs
    assert kwargs["location"] == "青岛"
    assert kwargs["vehicle_model"] == "T13J"
    assert kwargs["as_of_year"] == 2026
    assert kwargs["as_of_month"] == 7
    assert "bom_version" not in kwargs
    fee_kwargs = deps.welding_fee_repo.list_by_calc_scope.call_args.kwargs
    assert fee_kwargs["bom_version"] is None


@patch("app.services.costing.assembly_cost.calc.orchestrator.prep.VehicleModelService")
@patch(
    "app.services.costing.assembly_cost.calc.orchestrator.prep.assert_calc_ready",
    return_value=_ready(),
)
def test_prep_empty_as_of_month_raises(
    _ready_mock: MagicMock,
    vehicle_cls: MagicMock,
) -> None:
    vehicle_cls.return_value.require_introducible.return_value = ("青岛", "T13J")
    deps = MagicMock()
    deps.bom_node_repo.list_as_of_trees.return_value = []

    with pytest.raises(BusinessException, match="2026 年 07 月没有有效期内的 BOM 树"):
        prepare_calc_run(MagicMock(), deps, _dto(), ProgressNotifier())


def test_collect_calc_ready_uses_as_of_trees() -> None:
    deps = MagicMock()
    deps.bom_node_repo.list_as_of_trees.return_value = []
    deps.stamping_cost_repo.count_calc_success_with_unit_cost.return_value = 0
    deps.annual_price_repo.count_with_unit_price.return_value = 0
    deps.packaging_fee_repo.count_by_location_year.return_value = 0

    with (
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.VehicleModelService"
        ) as vehicle_cls,
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready.BomProcurementObjectRepository"
        ) as proc_cls,
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready._stamping_complete",
            return_value=(True, [], ""),
        ),
        patch(
            "app.services.costing.assembly_cost.calc.orchestrator.ready._welding_coverage",
            return_value=SimpleNamespace(complete=True, message="", fee_count=0, level_counts={}),
        ),
    ):
        vehicle_cls.return_value.require_introducible.return_value = ("青岛", "T13J")
        proc_cls.return_value.list_objects_by_location_vehicle.return_value = []
        vo = collect_calc_ready(
            MagicMock(),
            deps,
            year=2026,
            month=7,
            location="青岛",
            vehicle_model="T13J",
        )

    kwargs = deps.bom_node_repo.list_as_of_trees.call_args.kwargs
    assert kwargs["as_of_year"] == 2026
    assert kwargs["as_of_month"] == 7
    assert vo.ready is False
    assert vo.bom_version is None
    assert "没有有效期内的 BOM 树" in (vo.message or "")
