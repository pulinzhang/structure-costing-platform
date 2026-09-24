"""改图换号：clone 材料变更历史后写入新零件；回滚按历史 id 删除。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.models.masterdata.location import Location, LocationAlias
from app.models.masterdata.steel_grade_category import SteelGradeCategory
from app.models.masterdata.supplier import Supplier, SupplierAlias
from app.models.masterdata.vehicle_model import VehicleModel
from app.models.stamping.part import StampingPart, StampingProcess
from app.models.stamping.part_material_change import StampingPartMaterialChange
from app.models.stamping.tailor_weld_blank import StampingTailorWeldBlank
from app.repositories.masterdata.location.location_repository import LocationRepository
from app.schemas.dto.location_dto import LocationInsert
from app.schemas.dto.vehicle_model_dto import VehicleModelCreateDTO
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.services.stamping.part.engineering.design_change.clone import clone_revise_from_predecessor
from app.services.stamping.part.engineering.design_change.insert import (
    insert_material_changes_for_engineering_change,
)
from app.services.stamping.part.engineering.design_change.service import StampingDesignChangeService
from app.services.stamping.part.engineering.material_change import (
    MaterialChangeHistorySpec,
    StampingMaterialChangeService,
)

LOCATION = "芜湖"
VEHICLE = "T13J"
VERSION = "V3-01"
SUPPLIER = "安徽振华"
GRADE = "DC01"


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
            StampingPartMaterialChange.__table__,
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
    session.add(
        SteelGradeCategory(
            category_name="冷轧",
            category_seq=1,
            grade=GRADE,
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


def _part(db: Session, part_number: str) -> StampingPart:
    row = StampingPart(
        location=LOCATION,
        stamping_supplier=SUPPLIER,
        vehicle_model=VEHICLE,
        version=VERSION,
        part_number=part_number,
        material=GRADE,
        excel_filename="fixture.xlsx",
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.flush()
    return row


def _clone_history_onto(db: Session, old_part_id: int, new_part_id: int) -> list[tuple[int, int]]:
    design = StampingDesignChangeService()
    _, _, material_changes = clone_revise_from_predecessor(
        design.repository,
        design.process_repository,
        db,
        predecessor_id=old_part_id,
        new_part_number="unused",
        version=VERSION,
        effective_year=2025,
        effective_month=8,
        expiry_year=None,
        expiry_month=None,
        created_by="system",
        updated_by="system",
    )
    return insert_material_changes_for_engineering_change(
        db,
        part_id=new_part_id,
        material_changes=material_changes,
        current_user=SYSTEM_USER,
    )


def test_revise_copies_material_history_and_leaves_process_material(memory_db: Session) -> None:
    old_part = _part(memory_db, "403014115AA")
    new_part = _part(memory_db, "403014115AB")
    service = StampingMaterialChangeService()
    service.insert(
        memory_db,
        [
            MaterialChangeHistorySpec(
                part_id=old_part.id,
                effective_year=2025,
                effective_month=6,
                before_material=GRADE,
                after_material=GRADE,
                before_thickness=Decimal("1.5000"),
                after_thickness=Decimal("1.5000"),
            )
        ],
        SYSTEM_USER,
    )

    copied = _clone_history_onto(memory_db, old_part.id, new_part.id)

    assert len(copied) == 1
    new_rows = service.list_for_part(memory_db, new_part.id)
    old_rows = service.list_for_part(memory_db, old_part.id)
    assert len(new_rows) == 1
    assert new_rows[0].id == copied[0][1]
    assert new_rows[0].effective_year == old_rows[0].effective_year
    assert new_rows[0].effective_month == old_rows[0].effective_month
    assert new_rows[0].before_material == old_rows[0].before_material
    assert new_rows[0].after_material == old_rows[0].after_material
    assert new_rows[0].before_thickness == old_rows[0].before_thickness
    assert new_rows[0].after_thickness == old_rows[0].after_thickness
    memory_db.refresh(new_part)
    assert new_part.material == GRADE


def test_revise_without_history_adds_no_rows(memory_db: Session) -> None:
    old_part = _part(memory_db, "403014116AA")
    new_part = _part(memory_db, "403014116AB")
    copied = _clone_history_onto(memory_db, old_part.id, new_part.id)
    assert copied == []
    assert StampingMaterialChangeService().list_for_part(memory_db, new_part.id) == []


def test_design_change_rollback_deletes_copied_history_only(memory_db: Session) -> None:
    old_part = _part(memory_db, "403014117AA")
    new_part = _part(memory_db, "403014117AB")
    service = StampingMaterialChangeService()
    service.insert(
        memory_db,
        [
            MaterialChangeHistorySpec(
                part_id=old_part.id,
                effective_year=2025,
                effective_month=6,
                before_material=GRADE,
                after_material=GRADE,
                before_thickness=Decimal("1.5000"),
                after_thickness=Decimal("1.5000"),
            )
        ],
        SYSTEM_USER,
    )
    copied = _clone_history_onto(memory_db, old_part.id, new_part.id)
    _, new_history_id = copied[0]
    service.delete(memory_db, [new_history_id])
    StampingDesignChangeService().rollback_engineering_change_part(
        memory_db,
        after_part_id=new_part.id,
        before_part_id=old_part.id,
        current_user=SYSTEM_USER,
    )

    assert service.list_for_part(memory_db, new_part.id) == []
    assert len(service.list_for_part(memory_db, old_part.id)) == 1
    assert memory_db.get(StampingPart, new_part.id) is None
    assert memory_db.get(StampingPart, old_part.id) is not None
