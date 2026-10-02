"""材料清单上传：项目已登记即可，已结束的起止照抄。"""

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
from app.models.masterdata.vehicle_model import VehicleModel
from app.schemas.dto.vehicle_model_dto import VehicleModelCreateDTO
from app.services.bom.bom.upload.gates.validate import require_registered_project
from app.services.masterdata.vehicle_model.service import VehicleModelService
from tests.masterdata.location_fixtures import insert_sample_locations


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
        yield session
    finally:
        session.close()
        engine.dispose()


def test_ended_project_is_registered_and_period_is_copied(memory_db: Session) -> None:
    insert_sample_locations(memory_db)
    VehicleModelService().create(
        memory_db,
        VehicleModelCreateDTO(
            location="青岛",
            vehicle_model="T13J",
            effective_year=2020,
            effective_month=1,
            expiry_year=2024,
            expiry_month=12,
        ),
        current_user=SYSTEM_USER,
    )

    location, code = require_registered_project(memory_db, "青岛", "t13j")
    period = VehicleModelService().project_sop_period(memory_db, location, code)

    assert (location, code) == ("青岛", "T13J")
    assert period == (2020, 1, 2024, 12)


def test_missing_project_is_rejected(memory_db: Session) -> None:
    insert_sample_locations(memory_db)
    with pytest.raises(BusinessException, match="没有该项目"):
        require_registered_project(memory_db, "青岛", "T99")
