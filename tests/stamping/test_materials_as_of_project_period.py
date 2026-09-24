"""当月取材质：零件行仍有效，但项目已过期时不取牌号。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.masterdata.location import Location, LocationAlias
from app.models.masterdata.steel_grade_category import SteelGradeCategory
from app.models.masterdata.supplier import Supplier
from app.models.masterdata.vehicle_model import VehicleModel
from app.models.stamping.part import StampingPart
from app.models.stamping.part_material_change import StampingPartMaterialChange
from app.models.stamping.tailor_weld_blank import StampingTailorWeldBlank
from app.services.stamping.part.service import StampingPartService

LOCATION = "芜湖"
LIVE = "T13J"
STOPPED = "T99"


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
            Supplier.__table__,
            VehicleModel.__table__,
            SteelGradeCategory.__table__,
            StampingPart.__table__,
            StampingPartMaterialChange.__table__,
            StampingTailorWeldBlank.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    session.add(
        Location(
            location=LOCATION,
            is_enabled=True,
            sort_order=1,
            created_by="system",
            updated_by="system",
        )
    )
    session.add(
        VehicleModel(
            location=LOCATION,
            vehicle_model=LIVE,
            effective_year=2024,
            effective_month=1,
            created_by="system",
            updated_by="system",
        )
    )
    session.add(
        VehicleModel(
            location=LOCATION,
            vehicle_model=STOPPED,
            effective_year=2020,
            effective_month=1,
            expiry_year=2025,
            expiry_month=12,
            created_by="system",
            updated_by="system",
        )
    )
    for grade in ("DC04", "DC01", "B250P1"):
        session.add(
            SteelGradeCategory(
                category_name="冷轧",
                category_seq=1,
                grade=grade,
                created_by="system",
                updated_by="system",
            )
        )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _part(
    *,
    vehicle_model: str,
    part_number: str,
    material: str,
    is_tailor_welded: bool = False,
) -> StampingPart:
    return StampingPart(
        location=LOCATION,
        vehicle_model=vehicle_model,
        version="V1",
        part_number=part_number,
        material=material,
        thickness=Decimal("0.8"),
        effective_year=2020,
        effective_month=1,
        excel_filename="fixture.xlsx",
        is_tailor_welded=is_tailor_welded,
        created_by="system",
        updated_by="system",
    )


def test_expired_project_grade_is_dropped(memory_db: Session) -> None:
    live = _part(vehicle_model=LIVE, part_number="A", material="DC04")
    stopped = _part(
        vehicle_model=STOPPED,
        part_number="B",
        material="DC01",
        is_tailor_welded=True,
    )
    memory_db.add_all([live, stopped])
    memory_db.flush()
    memory_db.add(
        StampingTailorWeldBlank(
            part_id=stopped.id,
            parent_part_number=stopped.part_number,
            blank_seq=1,
            blank_part_number=f"{stopped.part_number}-1",
            material="B250P1",
            thickness=Decimal("1.2"),
            created_by="system",
            updated_by="system",
        )
    )
    memory_db.commit()

    rows = StampingPartService().list_materials_as_of(
        memory_db, location=LOCATION, year=2026, month=1
    )
    grades = {row["material"] for row in rows}
    assert grades == {"DC04"}
