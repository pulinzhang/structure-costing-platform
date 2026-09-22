"""冲压工艺删除：加工费 source_part_id RESTRICT 拦住单删与批量删除。"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.exceptions.base import BusinessException
from app.models.costing.stamping_part_cost import StampingPartCost
from app.models.masterdata.location import Location, LocationAlias
from app.models.masterdata.steel_grade_category import SteelGradeCategory
from app.models.masterdata.supplier import Supplier, SupplierAlias
from app.models.masterdata.vehicle_model import VehicleModel
from app.models.stamping.part import StampingPart, StampingProcess
from app.models.stamping.process_fee import StampingProcessFee
from app.models.stamping.process_fee_item import StampingProcessFeeItem
from app.models.stamping.tailor_weld_blank import StampingTailorWeldBlank
from app.repositories.masterdata.location.location_repository import LocationRepository
from app.schemas.dto.location_dto import LocationInsert
from app.schemas.dto.stamping_part_dto import StampingPartBatchDeleteDTO
from app.schemas.dto.vehicle_model_dto import VehicleModelCreateDTO
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.services.stamping.part.service import StampingPartService

LOCATION = "芜湖"
VEHICLE = "T13J"
VERSION = "V1"
PART_NUMBER = "502000001AA"
SUPPLIER = "安徽振华"


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
            Supplier.__table__,
            SupplierAlias.__table__,
            SteelGradeCategory.__table__,
            StampingPart.__table__,
            StampingProcess.__table__,
            StampingTailorWeldBlank.__table__,
            StampingProcessFee.__table__,
            StampingProcessFeeItem.__table__,
            StampingPartCost.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    LocationRepository().create(
        session,
        LocationInsert(
            location=LOCATION,
            is_enabled=True,
            sort_order=1,
            created_by="system",
            updated_by="system",
        ),
    )
    VehicleModelService().create(
        session,
        VehicleModelCreateDTO(
            location=LOCATION,
            vehicle_model=VEHICLE,
            effective_year=2020,
            effective_month=1,
        ),
        current_user=SYSTEM_USER,
    )
    session.add(
        Supplier(
            full_name=SUPPLIER,
            abbreviation="振华",
            erp_code="ZH01",
            is_enabled=True,
            sort_order=1,
            created_by="system",
            updated_by="system",
        )
    )
    session.flush()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _add_part(db: Session) -> StampingPart:
    part = StampingPart(
        location=LOCATION,
        stamping_supplier=SUPPLIER,
        vehicle_model=VEHICLE,
        version=VERSION,
        part_number=PART_NUMBER,
        excel_filename="fixture.xlsx",
        created_by="system",
        updated_by="system",
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


def _add_fee(db: Session, part: StampingPart) -> StampingProcessFee:
    fee = StampingProcessFee(
        year=2026,
        location=part.location,
        stamping_supplier=SUPPLIER,
        vehicle_model=part.vehicle_model,
        version=part.version,
        source_part_id=part.id,
        part_number=part.part_number,
        created_by="system",
        updated_by="system",
    )
    db.add(fee)
    db.commit()
    db.refresh(fee)
    return fee


def test_delete_part_without_fee(memory_db: Session) -> None:
    part = _add_part(memory_db)
    StampingPartService().delete(memory_db, part.id)
    assert memory_db.get(StampingPart, part.id) is None


def test_delete_part_blocked_when_fee_exists(memory_db: Session) -> None:
    part = _add_part(memory_db)
    fee = _add_fee(memory_db, part)

    with pytest.raises(BusinessException, match="冲压加工费列表") as caught:
        StampingPartService().delete(memory_db, part.id)
    assert "2026年" in caught.value.message
    assert "未审核" in caught.value.message
    assert "冲压零件价格一览" not in caught.value.message

    assert memory_db.get(StampingPart, part.id) is not None
    memory_db.delete(fee)
    memory_db.commit()
    StampingPartService().delete(memory_db, part.id)
    assert memory_db.get(StampingPart, part.id) is None


def test_batch_delete_blocked_when_fee_exists(memory_db: Session) -> None:
    part = _add_part(memory_db)
    _add_fee(memory_db, part)

    with pytest.raises(BusinessException, match="冲压加工费列表") as caught:
        StampingPartService().batch_delete(
            memory_db,
            StampingPartBatchDeleteDTO(
                location=LOCATION,
                vehicle_model=VEHICLE,
                version=VERSION,
            ),
        )
    assert "2026年" in caught.value.message
    assert memory_db.get(StampingPart, part.id) is not None


def _add_cost(db: Session, part: StampingPart, *, approved: bool = False) -> StampingPartCost:
    cost = StampingPartCost(
        year=2026,
        month=1,
        location=part.location,
        stamping_supplier=part.stamping_supplier,
        vehicle_model=part.vehicle_model,
        version=part.version,
        source_part_id=part.id,
        part_number=part.part_number,
        audit_status="approved" if approved else "pending",
        created_by="system",
        updated_by="system",
    )
    db.add(cost)
    db.commit()
    db.refresh(cost)
    return cost


def test_delete_part_blocked_by_part_cost(memory_db: Session) -> None:
    part = _add_part(memory_db)
    cost = _add_cost(memory_db, part)

    with pytest.raises(BusinessException, match="冲压零件价格一览") as caught:
        StampingPartService().delete(memory_db, part.id)
    assert "2026年01月" in caught.value.message
    assert "未审核" in caught.value.message
    assert "加工费" not in caught.value.message
    assert memory_db.get(StampingPart, part.id) is not None

    memory_db.query(StampingPartCost).filter(StampingPartCost.id == cost.id).delete()
    memory_db.commit()
    StampingPartService().delete(memory_db, part.id)
    assert memory_db.get(StampingPart, part.id) is None


def test_delete_part_blocked_by_approved_part_cost(memory_db: Session) -> None:
    part = _add_part(memory_db)
    _add_cost(memory_db, part, approved=True)

    with pytest.raises(BusinessException, match="已审核") as caught:
        StampingPartService().delete(memory_db, part.id)
    assert "反审核" in caught.value.message
    assert "冲压零件价格一览" in caught.value.message


def test_delete_part_blocked_by_fee_and_part_cost(memory_db: Session) -> None:
    part = _add_part(memory_db)
    _add_fee(memory_db, part)
    _add_cost(memory_db, part)

    with pytest.raises(BusinessException) as caught:
        StampingPartService().delete(memory_db, part.id)
    assert "冲压零件价格一览" in caught.value.message
    assert "冲压加工费列表" in caught.value.message


def test_rollback_message_uses_cost_row_scope(memory_db: Session) -> None:
    from app.common.engineering_change_gates import EFFECT_PROCESS_PART
    from app.services.bom.bom.delete_block import explain_rollback_blocked

    part = _add_part(memory_db)
    _add_cost(memory_db, part, approved=True)
    message = explain_rollback_blocked(
        memory_db,
        [(EFFECT_PROCESS_PART, part.id)],
        location="别处",
        vehicle_model="别的项目",
    )
    assert "冲压零件价格一览" in message
    assert "已审核" in message
    assert LOCATION in message
    assert "工程变更 → 工程变更单列表" in message
    assert "别处" not in message


def test_orphan_source_part_id_rejected(memory_db: Session) -> None:
    with pytest.raises(IntegrityError):
        memory_db.add(
            StampingPartCost(
                year=2026,
                month=1,
                location=LOCATION,
                stamping_supplier=SUPPLIER,
                vehicle_model=VEHICLE,
                version=VERSION,
                source_part_id=99999,
                part_number="ghost",
                created_by="system",
                updated_by="system",
            )
        )
        memory_db.commit()
    memory_db.rollback()
