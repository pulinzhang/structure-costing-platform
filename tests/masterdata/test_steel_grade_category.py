"""牌号分类档案：规范化与手工 CRUD。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.common.steel_grade import stored_grade
from app.common.steel_grade_category import (
    normalize_category_name,
    seq_for_category,
)
from app.database import Base
from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.steel_grade_category import SteelGradeCategory
from app.models.masterdata.steel_mill import SteelMill
from app.models.yishiyiyi.steel_base_price import SteelBasePrice
from app.schemas.dto.steel_grade_category_dto import (
    SteelGradeCategoryCreate,
    SteelGradeCategoryQuery,
    SteelGradeCategoryUpdate,
)
from app.services.masterdata.steel_grade_category.seed import SEED_STEEL_GRADE_CATEGORIES
from app.services.masterdata.steel_grade_category.service import (
    SteelGradeCategoryService,
)


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
            SteelGradeCategory.__table__,
            SteelMill.__table__,
            SteelBasePrice.__table__,
        ],
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


def test_ensure_seed_if_empty_writes_production_catalog(memory_db: Session) -> None:
    service = _service()
    service.ensure_seed_if_empty(memory_db)
    items, total = service.paginate(memory_db, SteelGradeCategoryQuery(page=1, size=100))
    assert total == len(SEED_STEEL_GRADE_CATEGORIES)
    grades = {row.grade for row in items}
    assert "DC01 HC180YD+Z" not in grades
    assert not any(grade.startswith("POLICY_TEST_") for grade in grades)
    assert {"DC01", "DC03", "DC04", "DC51D+Z", "QSTE420TM"} <= grades
    assert {"B180H1", "HC500/780DPD+Z", "QSTE460TM", "S355MC"} <= grades
    assert "DCO3" not in grades
    assert "DCO4" not in grades
    assert all(grade == stored_grade(grade) for grade in grades)
    by_grade = {row.grade: row.category_name for row in items}
    assert by_grade["DC01"] == "冷轧"
    assert by_grade["DC51D+Z"] == "镀锌"
    assert by_grade["QSTE420TM"] == "酸洗"
    assert by_grade["B180H1"] == "冷轧"
    assert by_grade["HC500/780DPD+Z"] == "镀锌"
    assert by_grade["QSTE460TM"] == "酸洗"

    service.ensure_seed_if_empty(memory_db)
    _, again = service.paginate(memory_db, SteelGradeCategoryQuery(page=1, size=100))
    assert again == total


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
        SteelGradeCategoryUpdate(grade="  dc01  ", category_name="镀锌", remark=None),
        current_user=SYSTEM_USER,
    )
    assert updated.grade == "DC01"
    assert updated.id == created.id
    assert updated.category_name == "镀锌"
    assert updated.category_seq == 2

    renamed = service.update(
        memory_db,
        created.id,
        SteelGradeCategoryUpdate(grade="dco1"),
        current_user=SYSTEM_USER,
    )
    assert renamed.grade == "DCO1"
    assert service.get_by_grade(memory_db, "DC01") is None

    service.delete(memory_db, created.id)
    with pytest.raises(NotFoundException):
        service.get_by_id(memory_db, created.id)


def test_paginate_sorts_by_seq_then_grade(memory_db: Session) -> None:
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

    items, total = service.paginate(memory_db, SteelGradeCategoryQuery(page=1, size=20))
    assert total == 3
    assert [row.grade for row in items] == ["DC01", "DC51D+Z", "SPCC"]

    cold, cold_total = service.paginate(
        memory_db, SteelGradeCategoryQuery(page=1, size=20, category_name="冷轧")
    )
    assert cold_total == 1
    assert cold[0].grade == "DC01"


def test_get_by_grade_and_map_grades(memory_db: Session) -> None:
    service = _service()
    service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC01", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    assert service.get_by_grade(memory_db, "DC01") is not None
    assert service.get_by_grade(memory_db, "MISSING") is None
    mapped = service.map_grades(memory_db, ["DC01", "MISSING", " DC01 "])
    assert set(mapped) == {"DC01"}
    assert mapped["DC01"].category_name == "冷轧"


def test_require_matched_grades_rewrites_and_rejects_missing(memory_db: Session) -> None:
    service = _service()
    service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC01", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    matched = service.require_matched_grades(memory_db, ["DCO1", "dc01", ""])
    assert matched["DCO1"].grade == "DC01"
    assert matched["dc01"].grade == "DC01"
    single = service.require_matched_grade(memory_db, "dco1")
    assert single is not None
    assert single.grade == "DC01"
    assert service.bind_stored_grades(memory_db, ["DCO1", "", "dc01"]) == [
        "DC01",
        None,
        "DC01",
    ]
    assert service.bind_stored_grade(memory_db, "") is None
    with pytest.raises(BusinessException, match="主数据 → 牌号分类") as missing:
        service.require_matched_grades(memory_db, ["DC01", "HC340/590DP"])
    assert "HC340/590DP" in str(missing.value)


def test_match_by_grade_key_returns_archive_row(memory_db: Session) -> None:
    service = _service()
    service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC01", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    vo = service.match_by_grade_key(memory_db, "DCO1")
    assert vo is not None
    assert vo.grade == "DC01"
    assert vo.category_name == "冷轧"
    assert service.match_by_grade_key(memory_db, "MISSING") is None
    again = service.match_by_grade_key(memory_db, "dc01")
    assert again is not None
    assert again.grade == "DC01"
    with pytest.raises(BusinessException, match="牌号已存在"):
        service.create(
            memory_db,
            SteelGradeCategoryCreate(grade="DCO1", category_name="冷轧"),
            current_user=SYSTEM_USER,
        )


def test_create_uppercases_and_keeps_letter_o(memory_db: Session) -> None:
    service = _service()
    created = service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="  dco3  ", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    assert created.grade == "DCO3"
    assert service.get_by_grade(memory_db, "DC03") is None


def test_update_grade_rejects_match_key_conflict(memory_db: Session) -> None:
    service = _service()
    service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC03", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    other = service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC01", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    with pytest.raises(BusinessException, match="牌号已存在") as conflict:
        service.update(
            memory_db,
            other.id,
            SteelGradeCategoryUpdate(grade="DCO3"),
            current_user=SYSTEM_USER,
        )
    assert conflict.value.code == 409


def test_update_grade_cascades_base_price(memory_db: Session) -> None:
    service = _service()
    created = service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC01", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    mill = SteelMill(
        abbreviation="马钢",
        full_name="马钢",
        is_enabled=True,
        sort_order=1,
        created_by="system",
        updated_by="system",
    )
    memory_db.add(mill)
    memory_db.flush()
    memory_db.add(
        SteelBasePrice(
            year=2026,
            month=1,
            location="芜湖",
            steel_mill="马钢",
            canonical_steel_mill="马钢",
            steel_mill_id=mill.id,
            category_name="冷轧",
            grade="DC01",
            spec="1.00*1250.00",
            thick=Decimal("1.00"),
            width=Decimal("1250.00"),
            base_price=Decimal("4000.00"),
            processing_fee=Decimal("120.00"),
            excel_filename="fixture.xlsx",
            sheet_name="定价表",
            excel_row=1,
            created_by="system",
            updated_by="system",
        )
    )
    memory_db.commit()
    renamed = service.update(
        memory_db,
        created.id,
        SteelGradeCategoryUpdate(grade="DC02"),
        current_user=SYSTEM_USER,
    )
    assert renamed.grade == "DC02"
    assert renamed.id == created.id
    assert service.get_by_grade(memory_db, "DC01") is None
    assert [row.grade for row in memory_db.query(SteelBasePrice).all()] == ["DC02"]


def test_base_price_write_uses_archive_grade_and_category(memory_db: Session) -> None:
    from app.schemas.dto.steel_base_price_dto import SteelBasePriceWrite
    from app.services.yishiyiyi.base_price.importing.service import (
        _canonicalize_grade_and_category,
    )

    service = _service()
    service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC01", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    write = SteelBasePriceWrite(
        year=2026,
        month=1,
        location="青岛",
        steel_mill="本钢",
        steel_mill_id=1,
        canonical_steel_mill="本钢",
        category_name="镀锌钢",
        grade="DCO1",
        thick=Decimal("1.00"),
        width=Decimal("1250.00"),
        base_price=Decimal("4000.00"),
        processing_fee=Decimal("120.00"),
        excel_filename="a.xlsx",
        sheet_name="Sheet1",
        excel_row=6,
    )
    warnings = _canonicalize_grade_and_category(memory_db, [write])
    assert write.grade == "DC01"
    assert write.category_name == "冷轧"
    assert any("镀锌钢" in item and "冷轧" in item for item in warnings)

    write.grade = "   "
    with pytest.raises(BusinessException, match="牌号不能为空"):
        _canonicalize_grade_and_category(memory_db, [write])


def test_delete_blocked_when_base_price_references_grade(memory_db: Session) -> None:
    service = _service()
    created = service.create(
        memory_db,
        SteelGradeCategoryCreate(grade="DC01", category_name="冷轧"),
        current_user=SYSTEM_USER,
    )
    mill = SteelMill(
        abbreviation="马钢",
        full_name="马钢",
        is_enabled=True,
        sort_order=1,
        created_by="system",
        updated_by="system",
    )
    memory_db.add(mill)
    memory_db.flush()
    memory_db.add(
        SteelBasePrice(
            year=2026,
            month=1,
            location="芜湖",
            steel_mill="马钢",
            canonical_steel_mill="马钢",
            steel_mill_id=mill.id,
            category_name="冷轧",
            grade="DC01",
            spec="1.00*1250.00",
            thick=Decimal("1.00"),
            width=Decimal("1250.00"),
            base_price=Decimal("4000.00"),
            processing_fee=Decimal("120.00"),
            excel_filename="fixture.xlsx",
            sheet_name="定价表",
            excel_row=1,
            created_by="system",
            updated_by="system",
        )
    )
    memory_db.commit()
    with pytest.raises(BusinessException, match="仍被引用，不能删除"):
        service.delete(memory_db, created.id)
    assert service.get_by_id(memory_db, created.id).grade == "DC01"
