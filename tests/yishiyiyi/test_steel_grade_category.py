"""牌号分类档案：规范化、CRUD、ensure_grades、工艺收牌号。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.common.steel_grade_category import (
    normalize_category_name,
    seq_for_category,
)
from app.database import Base
from app.exceptions.base import BusinessException, NotFoundException
from app.models.yishiyiyi.steel_base_price import SteelBasePrice
from app.models.yishiyiyi.steel_grade_category import SteelGradeCategory
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.tailor_weld import (
    TailorWeldAssemblyParsed,
    TailorWeldBlankParsed,
)
from app.schemas.dto.steel_grade_category_dto import (
    GradeEnsureItem,
    SteelGradeCategoryCreate,
    SteelGradeCategoryQuery,
    SteelGradeCategoryUpdate,
)
from app.services.stamping.upload.stamping_upload import StampingUploadService
from app.services.yishiyiyi.steel_grade_category import (
    SOURCE_BASE_PRICE,
    SOURCE_STAMPING_UPLOAD,
    SteelGradeCategoryService,
)


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[SteelGradeCategory.__table__, SteelBasePrice.__table__],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _service() -> SteelGradeCategoryService:
    return SteelGradeCategoryService()


def _add_base_price(
    db: Session,
    grade: str,
    category_name: str,
    excel_row: int,
    steel_mill: str = "马钢",
) -> None:
    db.add(
        SteelBasePrice(
            year=2026,
            month=1,
            location="芜湖",
            steel_mill=steel_mill,
            category_name=category_name,
            grade=grade,
            spec="1.00*1250.00",
            thick=Decimal("1.00"),
            width=Decimal("1250.00"),
            base_price=Decimal("4000.00"),
            processing_fee=Decimal("120.00"),
            excel_filename="fixture.xlsx",
            sheet_name="定价表",
            excel_row=excel_row,
            created_by="system",
            updated_by="system",
        )
    )


def test_normalize_category_aliases() -> None:
    assert normalize_category_name("冷轧钢") == "冷轧"
    assert normalize_category_name("冷扎") == "冷轧"
    assert normalize_category_name("镀锌钢") == "镀锌"
    assert normalize_category_name("酸洗钢") == "酸洗"
    assert normalize_category_name(" 冷轧 ") == "冷轧"
    assert normalize_category_name("") is None
    assert normalize_category_name("热轧") == "热轧"
    assert seq_for_category("冷轧") == 1
    assert seq_for_category("镀锌") == 2
    assert seq_for_category("酸洗") == 3
    assert seq_for_category(None) is None


def test_create_update_delete_unique_grade(memory_db: Session) -> None:
    service = _service()
    created = service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC01", category_name="冷轧钢", remark="手建"),
        current_user=SYSTEM_USER,
    )
    assert created.grade == "DC01"
    assert created.category_name == "冷轧"
    assert created.category_seq == 1
    assert created.source == "manual"

    with pytest.raises(BusinessException) as duplicate:
        service.create(
            memory_db,
            SteelGradeCategoryCreate(grade="DC01", category_name="冷轧"),
            current_user=SYSTEM_USER,
        )
    assert duplicate.value.code == 409

    updated = service.update(
        memory_db,
        created.id,
        SteelGradeCategoryUpdate(category_name="镀锌", remark=None),
        current_user=SYSTEM_USER,
    )
    assert updated.category_name == "镀锌"
    assert updated.category_seq == 2

    service.delete(memory_db, created.id)
    with pytest.raises(NotFoundException):
        service.get_by_id(memory_db, created.id)


def test_paginate_sorts_seq_then_uncategorized(memory_db: Session) -> None:
    service = _service()
    service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="SPCC", category_name="酸洗"),
        current_user=SYSTEM_USER,
    )
    service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC51D+Z", category_name="镀锌"),
        current_user=SYSTEM_USER,
    )
    service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC01", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    memory_db.add(
        SteelGradeCategory(
            grade="UNKNOWN",
            category_name=None,
            category_seq=None,
            source="stamping_upload",
            created_by="system",
            updated_by="system",
        )
    )
    memory_db.commit()

    items, total = service.paginate(memory_db, SteelGradeCategoryQuery(page=1, size=20))
    assert total == 4
    assert [row.grade for row in items] == ["DC01", "DC51D+Z", "SPCC", "UNKNOWN"]

    pending, pending_total = service.paginate(
        memory_db, SteelGradeCategoryQuery(page=1, size=20, uncategorized=True)
    )
    assert pending_total == 1
    assert pending[0].grade == "UNKNOWN"


def test_ensure_insert_skip_claim_conflict(memory_db: Session) -> None:
    service = _service()
    first = service.ensure_grades(
        memory_db,
        [
            GradeEnsureItem(grade="", category_name="冷轧"),
            GradeEnsureItem(grade="DC01", category_name="冷轧"),
            GradeEnsureItem(grade="DC01", category_name="冷轧"),
        ],
        source=SOURCE_BASE_PRICE,
        current_user=SYSTEM_USER,
    )
    memory_db.commit()
    assert first.inserted_count == 1
    assert first.skipped_count == 0

    skip_existing = service.ensure_grades(
        memory_db,
        [GradeEnsureItem(grade="DC01", category_name="冷轧")],
        source=SOURCE_BASE_PRICE,
        current_user=SYSTEM_USER,
    )
    assert skip_existing.inserted_count == 0
    assert skip_existing.skipped_count == 1

    conflict = service.ensure_grades(
        memory_db,
        [GradeEnsureItem(grade="DC01", category_name="镀锌")],
        source=SOURCE_BASE_PRICE,
        current_user=SYSTEM_USER,
    )
    assert conflict.inserted_count == 0
    assert conflict.conflicts
    assert "DC01" in conflict.conflicts[0]
    assert service.get_by_grade(memory_db, "DC01").category_name == "冷轧"

    memory_db.add(
        SteelGradeCategory(
            grade="HC180Y",
            category_name=None,
            category_seq=None,
            source="stamping_upload",
            created_by="system",
            updated_by="system",
        )
    )
    memory_db.flush()
    claimed = service.ensure_grades(
        memory_db,
        [GradeEnsureItem(grade="HC180Y", category_name="冷轧")],
        source=SOURCE_BASE_PRICE,
        current_user=SYSTEM_USER,
    )
    memory_db.commit()
    assert claimed.claimed_count == 1
    assert service.get_by_grade(memory_db, "HC180Y").category_name == "冷轧"
    assert service.get_by_grade(memory_db, "HC180Y").category_seq == 1


def test_ensure_base_price_skips_unknown_category(memory_db: Session) -> None:
    result = _service().ensure_grades(
        memory_db,
        [GradeEnsureItem(grade="XX123", category_name="热轧")],
        source=SOURCE_BASE_PRICE,
        current_user=SYSTEM_USER,
    )
    memory_db.commit()
    assert result.inserted_count == 0
    assert result.skipped_count == 1
    assert _service().get_by_grade(memory_db, "XX123") is None


def test_ensure_stamping_inserts_uncategorized_and_fills_from_base(
    memory_db: Session,
) -> None:
    service = _service()
    unclassified = service.ensure_grades(
        memory_db,
        [GradeEnsureItem(grade="NEW01")],
        source=SOURCE_STAMPING_UPLOAD,
        current_user=SYSTEM_USER,
    )
    memory_db.commit()
    assert unclassified.inserted_count == 1
    row = service.get_by_grade(memory_db, "NEW01")
    assert row is not None
    assert row.category_name is None
    assert row.source == SOURCE_STAMPING_UPLOAD

    _add_base_price(memory_db, "DC04", "冷轧", 1, steel_mill="马钢")
    _add_base_price(memory_db, "DC04", "冷轧", 2, steel_mill="本钢")
    _add_base_price(memory_db, "DC04", "镀锌", 3, steel_mill="首钢")
    memory_db.commit()
    filled = service.ensure_grades(
        memory_db,
        [GradeEnsureItem(grade="DC04")],
        source=SOURCE_STAMPING_UPLOAD,
        current_user=SYSTEM_USER,
    )
    memory_db.commit()
    assert filled.inserted_count == 1
    assert service.get_by_grade(memory_db, "DC04").category_name == "冷轧"


def test_ensure_batch_two_categories_conflict(memory_db: Session) -> None:
    result = _service().ensure_grades(
        memory_db,
        [
            GradeEnsureItem(grade="DC01", category_name="冷轧"),
            GradeEnsureItem(grade="DC01", category_name="镀锌"),
        ],
        source=SOURCE_BASE_PRICE,
        current_user=SYSTEM_USER,
    )
    memory_db.commit()
    assert result.inserted_count == 1
    assert result.conflicts
    row = _service().get_by_grade(memory_db, "DC01")
    assert row is not None
    assert row.category_name == "冷轧"


def test_collect_upload_grades_includes_blanks_and_skips_empty() -> None:
    parts = [
        Part(material="DC01"),
        Part(material=" DC01 "),
        Part(material=""),
        Part(material=None),
    ]
    assemblies = [
        TailorWeldAssemblyParsed(
            parent_part_number="P1",
            excel_row_start=1,
            excel_row_end=2,
            material="HC220YD+Z",
            blanks=[
                TailorWeldBlankParsed(
                    blank_seq=1,
                    excel_row_start=1,
                    excel_row_end=1,
                    material="HC340/590DP",
                ),
                TailorWeldBlankParsed(
                    blank_seq=2,
                    excel_row_start=2,
                    excel_row_end=2,
                    material="",
                ),
            ],
        )
    ]
    items = StampingUploadService._collect_upload_grades(parts, assemblies)
    grades = [item.grade for item in items]
    assert grades == ["DC01", "HC220YD+Z", "HC340/590DP"]
