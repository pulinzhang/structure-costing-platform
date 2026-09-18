"""冲压工艺导入：材质与基价同一套 match_by_grade_key 改写。"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.models.masterdata.steel_grade_category import SteelGradeCategory
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.tailor_weld import (
    TailorWeldAssemblyParsed,
    TailorWeldBlankParsed,
)
from app.schemas.dto.steel_grade_category_dto import SteelGradeCategoryCreate
from app.services.masterdata.steel_grade_category import SteelGradeCategoryService
from app.services.stamping.upload.materials import canonicalize_materials


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

    Base.metadata.create_all(bind=engine, tables=[SteelGradeCategory.__table__])
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_canonicalize_materials_rewrites_letter_o(memory_db: Session) -> None:
    SteelGradeCategoryService().create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC01", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    parts = [Part(part_number="P1", material="dco1")]
    blank = TailorWeldBlankParsed(
        blank_seq=1,
        excel_row_start=1,
        excel_row_end=1,
        material="DCO1",
    )
    assemblies = [
        TailorWeldAssemblyParsed(
            parent_part_number="P2",
            excel_row_start=1,
            excel_row_end=1,
            material="",
            blanks=[blank],
        )
    ]
    canonicalize_materials(memory_db, parts, assemblies)
    assert parts[0].material == "DC01"
    assert assemblies[0].material is None
    assert blank.material == "DC01"


def test_tailor_blank_canonical_material_rewrites_letter_o(memory_db: Session) -> None:
    SteelGradeCategoryService().create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC01", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    assert SteelGradeCategoryService().bind_stored_grade(memory_db, "dco1") == "DC01"
    assert SteelGradeCategoryService().bind_stored_grade(memory_db, "") is None
