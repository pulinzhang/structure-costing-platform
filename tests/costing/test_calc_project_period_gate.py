"""计算入口：账期问项目期。列表 as_of 不在本文件（见 landing）。"""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.exceptions.base import BusinessException
from app.models.masterdata.location import Location, LocationAlias
from app.models.masterdata.vehicle_model import VehicleModel
from app.schemas.dto.assembly_cost_dto import AssemblyCostCalcDTO
from app.schemas.dto.bom_welding_fee_dto import BomWeldingFeeCalcDTO
from app.schemas.dto.stamping_die_fee_dto import StampingDieFeeCalcDTO
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostCalcDTO
from app.schemas.dto.stamping_process_fee_dto import StampingProcessFeeCalcDTO
from app.schemas.dto.vehicle_model_dto import VehicleModelCreateDTO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.welding_fee.calc.orchestrator.orchestrator import (
    BomWeldingFeeCalcOrchestrator,
)
from app.services.bom.welding_fee.calc.orchestrator.prep import (
    prepare_calc_run as prepare_welding,
)
from app.services.bom.welding_fee.calc.orchestrator.progress import (
    ProgressNotifier as WeldingProgress,
)
from app.services.bom.welding_fee.calc.orchestrator.ready import (
    collect_calc_ready as welding_ready,
)
from app.services.costing.assembly_cost.assembly_cost_service import AssemblyCostService
from app.services.costing.assembly_cost.calc.orchestrator.prep import (
    prepare_calc_run as prepare_assembly,
)
from app.services.costing.assembly_cost.calc.orchestrator.progress import (
    ProgressNotifier as AssemblyProgress,
)
from app.services.costing.assembly_cost.calc.orchestrator.ready import (
    collect_calc_ready as assembly_ready,
)
from app.services.costing.stamping_part_cost.calc.orchestrator.prep import (
    prepare_calc_run as prepare_part_cost,
)
from app.services.costing.stamping_part_cost.calc.orchestrator.progress import (
    ProgressNotifier as PartProgress,
)
from app.services.costing.stamping_part_cost.calc.orchestrator.ready import (
    collect_calc_ready as part_cost_ready,
)
from app.services.costing.stamping_part_cost.stamping_part_cost_service import (
    StampingPartCostService,
)
from app.services.masterdata.vehicle_model.vehicle_model_service import VehicleModelService
from app.services.stamping.die_fee.calc.orchestrator.orchestrator import (
    StampingDieFeeCalcOrchestrator,
)
from app.services.stamping.die_fee.calc.orchestrator.prep import (
    prepare_calc_run as prepare_die,
)
from app.services.stamping.die_fee.calc.orchestrator.progress import (
    ProgressNotifier as DieProgress,
)
from app.services.stamping.die_fee.calc.orchestrator.ready import (
    collect_calc_ready as die_ready,
)
from app.services.stamping.process_fee.calc.orchestrator.orchestrator import (
    StampingProcessFeeCalcOrchestrator,
)
from app.services.stamping.process_fee.calc.orchestrator.prep import (
    prepare_calc_run as prepare_process,
)
from app.services.stamping.process_fee.calc.orchestrator.progress import (
    ProgressNotifier as ProcessProgress,
)
from app.services.stamping.process_fee.calc.orchestrator.ready import (
    collect_calc_ready as process_ready,
)
from tests.masterdata.location_fixtures import insert_sample_locations

ARCHIVE = "项目一览"


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(
        bind=engine,
        tables=[
            Location.__table__,
            LocationAlias.__table__,
            VehicleModel.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        insert_sample_locations(session)
        VehicleModelService().create(
            session,
            VehicleModelCreateDTO(
                location="青岛",
                vehicle_model="T13J",
                effective_year=2026,
                effective_month=1,
                expiry_year=2026,
                expiry_month=6,
            ),
            current_user=SYSTEM_USER,
        )
        yield session
    finally:
        session.close()
        engine.dispose()


def _user() -> UserVO:
    return UserVO(id=1, username="tester", real_name="测试员")


def _lock() -> SimpleNamespace:
    return SimpleNamespace(id=1, calc_batch_id="batch-1")


def _monthly(*, month: int) -> StampingPartCostCalcDTO:
    return StampingPartCostCalcDTO(year=2026, month=month, location="青岛", vehicle_model="T13J")


def _assembly(*, month: int) -> AssemblyCostCalcDTO:
    return AssemblyCostCalcDTO(year=2026, month=month, location="青岛", vehicle_model="T13J")


def _annual(*, year: int) -> StampingProcessFeeCalcDTO:
    return StampingProcessFeeCalcDTO(year=year, location="青岛", vehicle_model="T13J")


def _die(*, year: int) -> StampingDieFeeCalcDTO:
    return StampingDieFeeCalcDTO(year=year, location="青岛", vehicle_model="T13J")


def _welding(*, year: int) -> BomWeldingFeeCalcDTO:
    return BomWeldingFeeCalcDTO(year=year, location="青岛", vehicle_model="T13J")


def _patch_async(module: str):
    return patch(f"{module}.AsyncTaskService")


def _task_service(async_cls: MagicMock) -> MagicMock:
    service = async_cls.return_value
    service.create_task.return_value = SimpleNamespace(task_id="task-1")
    return service


def test_monthly_start_calc_rejects_after_expiry(memory_db: Session) -> None:
    user = _user()
    with pytest.raises(BusinessException, match=ARCHIVE):
        StampingPartCostService().start_calc(memory_db, _monthly(month=7), user)
    with pytest.raises(BusinessException, match=ARCHIVE):
        AssemblyCostService().start_calc(memory_db, _assembly(month=7), user)


def test_monthly_start_calc_accepts_before_expiry(memory_db: Session) -> None:
    user = _user()
    with (
        patch(
            "app.services.costing.stamping_part_cost.calc_ops.begin_processing",
            return_value=_lock(),
        ) as part_begin,
        _patch_async("app.services.costing.stamping_part_cost.calc_ops") as part_async,
    ):
        _task_service(part_async)
        result = StampingPartCostService().start_calc(memory_db, _monthly(month=6), user)
    part_begin.assert_called_once()
    assert result.task_id == "task-1"

    assembly = AssemblyCostService()
    assembly.begin_processing = MagicMock(return_value=_lock())
    with _patch_async("app.services.costing.assembly_cost.assembly_cost_service") as assembly_async:
        _task_service(assembly_async)
        result = assembly.start_calc(memory_db, _assembly(month=6), user)
    assembly.begin_processing.assert_called_once()
    assert result.task_id == "task-1"


def test_annual_start_calc_rejects_without_year_overlap(memory_db: Session) -> None:
    user = _user()
    with pytest.raises(BusinessException, match=ARCHIVE):
        StampingProcessFeeCalcOrchestrator().start_calc(memory_db, _annual(year=2027), user)
    with pytest.raises(BusinessException, match=ARCHIVE):
        StampingDieFeeCalcOrchestrator().start_calc(memory_db, _die(year=2027), user)
    with pytest.raises(BusinessException, match=ARCHIVE):
        BomWeldingFeeCalcOrchestrator().start_calc(memory_db, _welding(year=2027), user)


def test_annual_start_calc_accepts_midyear_stop_same_year(memory_db: Session) -> None:
    user = _user()
    process = StampingProcessFeeCalcOrchestrator()
    process.begin_processing = MagicMock(return_value=_lock())
    with _patch_async(
        "app.services.stamping.process_fee.calc.orchestrator.orchestrator"
    ) as process_async:
        _task_service(process_async)
        result = process.start_calc(memory_db, _annual(year=2026), user)
    process.begin_processing.assert_called_once()
    assert result.task_id == "task-1"

    die = StampingDieFeeCalcOrchestrator()
    die.calc_log_service.begin_processing = MagicMock(return_value=_lock())
    with (
        patch(
            "app.services.stamping.die_fee.calc.orchestrator.orchestrator.count_approved",
            return_value=0,
        ),
        _patch_async("app.services.stamping.die_fee.calc.orchestrator.orchestrator") as die_async,
    ):
        _task_service(die_async)
        result = die.start_calc(memory_db, _die(year=2026), user)
    die.calc_log_service.begin_processing.assert_called_once()
    assert result.task_id == "task-1"

    welding = BomWeldingFeeCalcOrchestrator()
    welding.begin_processing = MagicMock(return_value=_lock())
    with _patch_async(
        "app.services.bom.welding_fee.calc.orchestrator.orchestrator"
    ) as welding_async:
        _task_service(welding_async)
        result = welding.start_calc(memory_db, _welding(year=2026), user)
    welding.begin_processing.assert_called_once()
    assert result.task_id == "task-1"


def test_prepare_rejects_expired_period(memory_db: Session) -> None:
    with pytest.raises(BusinessException, match=ARCHIVE):
        prepare_part_cost(memory_db, MagicMock(), _monthly(month=7), PartProgress())
    with pytest.raises(BusinessException, match=ARCHIVE):
        prepare_assembly(memory_db, MagicMock(), _assembly(month=7), AssemblyProgress())
    with pytest.raises(BusinessException, match=ARCHIVE):
        prepare_process(memory_db, MagicMock(), _annual(year=2027), ProcessProgress())
    with pytest.raises(BusinessException, match=ARCHIVE):
        prepare_die(memory_db, MagicMock(), _die(year=2027), DieProgress())
    with pytest.raises(BusinessException, match=ARCHIVE):
        prepare_welding(memory_db, MagicMock(), _welding(year=2027), WeldingProgress())


def test_ready_expired_period_is_not_http_error(memory_db: Session) -> None:
    deps = MagicMock()
    part = part_cost_ready(
        memory_db,
        deps,
        year=2026,
        month=7,
        location="青岛",
        vehicle_model="T13J",
    )
    assert part.can_calculate is False
    assert ARCHIVE in (part.message or "")
    deps.part_repo.list_with_processes.assert_not_called()

    assembly = assembly_ready(
        memory_db,
        deps,
        year=2026,
        month=7,
        location="青岛",
        vehicle_model="T13J",
    )
    assert assembly.ready is False
    assert ARCHIVE in (assembly.message or "")

    process = process_ready(
        memory_db,
        deps,
        year=2027,
        location="青岛",
        vehicle_model="T13J",
    )
    assert process.part_count == 0
    assert process.tonnage_rate_count == 0
    assert ARCHIVE in (process.message or "")
    deps.part_repo.list_with_processes.assert_not_called()

    die = die_ready(
        memory_db,
        deps,
        year=2027,
        location="青岛",
        vehicle_model="T13J",
    )
    assert die.part_count == 0
    assert die.calculable_count == 0
    assert ARCHIVE in (die.message or "")
    deps.die_repo.list_with_processes.assert_not_called()

    welding = welding_ready(
        memory_db,
        deps,
        year=2027,
        location="青岛",
        vehicle_model="T13J",
    )
    assert welding.unit_price_count == 0
    assert welding.levels == []
    assert ARCHIVE in (welding.message or "")
    deps.breakdown_repo.list_by_source_node_ids.assert_not_called()
