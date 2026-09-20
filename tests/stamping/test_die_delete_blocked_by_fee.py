"""模具布点删除：模具费 source_die_part_id RESTRICT 拦住按范围删除。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.exceptions.base import BusinessException
from app.models.masterdata.location import Location, LocationAlias
from app.models.masterdata.vehicle_model import VehicleModel
from app.models.stamping.die import StampingDiePart, StampingDieProcess
from app.models.stamping.die_fee import StampingDieFee
from app.models.stamping.die_fee_item import StampingDieFeeItem
from app.repositories.masterdata.location.location_repository import LocationRepository
from app.schemas.dto.location_dto import LocationInsert
from app.schemas.dto.stamping_die_dto import StampingDieScopeDTO
from app.schemas.dto.vehicle_model_dto import VehicleModelCreateDTO
from app.services.masterdata.vehicle_model.vehicle_model_service import VehicleModelService
from app.services.stamping.die.crud.service import StampingDieService

LOCATION = "芜湖"
VEHICLE = "T13J"
PART_NUMBER = "502000001AA"


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
            StampingDiePart.__table__,
            StampingDieProcess.__table__,
            StampingDieFee.__table__,
            StampingDieFeeItem.__table__,
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
    session.flush()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _add_die_part(db: Session) -> StampingDiePart:
    part = StampingDiePart(
        location=LOCATION,
        vehicle_model=VEHICLE,
        part_number=PART_NUMBER,
        excel_filename="fixture.xlsx",
        effective_year=2020,
        effective_month=1,
        created_by="system",
        updated_by="system",
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


def _add_fee(db: Session, part: StampingDiePart) -> StampingDieFee:
    fee = StampingDieFee(
        year=2026,
        location=part.location,
        vehicle_model=part.vehicle_model,
        part_number=part.part_number,
        source_die_part_id=part.id,
        price_kind="steel_plate",
        unit_price=Decimal("5.0000"),
        allocation_qty=Decimal("10"),
        die_fee=Decimal("1.0000"),
        final_die_fee=Decimal("1.0000"),
        created_by="system",
        updated_by="system",
    )
    db.add(fee)
    db.commit()
    db.refresh(fee)
    return fee


def test_delete_scope_without_fee(memory_db: Session) -> None:
    part = _add_die_part(memory_db)
    part_id = part.id
    result = StampingDieService().delete_scope(
        memory_db,
        StampingDieScopeDTO(location=LOCATION, vehicle_model=VEHICLE),
    )
    assert result.deleted_parts == 1
    assert memory_db.get(StampingDiePart, part_id) is None


def test_delete_scope_blocked_when_fee_exists(memory_db: Session) -> None:
    part = _add_die_part(memory_db)
    part_id = part.id
    fee = _add_fee(memory_db, part)

    with pytest.raises(BusinessException, match="仍被冲压模具费引用"):
        StampingDieService().delete_scope(
            memory_db,
            StampingDieScopeDTO(location=LOCATION, vehicle_model=VEHICLE),
        )

    assert memory_db.get(StampingDiePart, part_id) is not None
    memory_db.delete(fee)
    memory_db.commit()
    result = StampingDieService().delete_scope(
        memory_db,
        StampingDieScopeDTO(location=LOCATION, vehicle_model=VEHICLE),
    )
    assert result.deleted_parts == 1
    assert memory_db.get(StampingDiePart, part_id) is None
