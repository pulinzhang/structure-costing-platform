"""冲压工艺删除：加工费 source_part_id RESTRICT 拦住单删与批量删除。"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.exceptions.base import BusinessException
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

    with pytest.raises(BusinessException, match="仍被冲压加工费引用"):
        StampingPartService().delete(memory_db, part.id)

    assert memory_db.get(StampingPart, part.id) is not None
    memory_db.delete(fee)
    memory_db.commit()
    StampingPartService().delete(memory_db, part.id)
    assert memory_db.get(StampingPart, part.id) is None


def test_batch_delete_blocked_when_fee_exists(memory_db: Session) -> None:
    part = _add_part(memory_db)
    _add_fee(memory_db, part)

    with pytest.raises(BusinessException, match="仍被冲压加工费引用"):
        StampingPartService().batch_delete(
            memory_db,
            StampingPartBatchDeleteDTO(
                location=LOCATION,
                vehicle_model=VEHICLE,
                version=VERSION,
            ),
        )
    assert memory_db.get(StampingPart, part.id) is not None
