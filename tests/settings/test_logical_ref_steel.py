"""逻辑引用样例：零件工艺材料与材料变更按账期挡住钢材联动。"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.exceptions.base import BusinessException
from app.models.settings.logical_ref.model import LogicalRef, LogicalRefFilter
from app.services.settings.logical_ref.seed import ensure_logical_ref_seed
from app.services.settings.logical_ref.service import ensure_logical_deletable
from app.services.stamping.part.engineering import material_change as material_change_module
from app.services.stamping.part.engineering.material_change import StampingMaterialChangeService


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session = sessionmaker(bind=engine)()
    session.execute(
        text(
            "CREATE TABLE stamping_parts ("
            "id INTEGER PRIMARY KEY, location TEXT, material TEXT, thickness NUMERIC, "
            "effective_year INTEGER, effective_month INTEGER, "
            "expiry_year INTEGER, expiry_month INTEGER, "
            "is_tailor_welded INTEGER NOT NULL DEFAULT 0, "
            "is_offal_nested INTEGER NOT NULL DEFAULT 0, "
            "is_scrap_byproduct INTEGER NOT NULL DEFAULT 0)"
        )
    )
    session.execute(
        text(
            "CREATE TABLE stamping_part_material_changes ("
            "id INTEGER PRIMARY KEY, part_id INTEGER NOT NULL, "
            "effective_year INTEGER NOT NULL, effective_month INTEGER NOT NULL, "
            "after_material TEXT)"
        )
    )
    session.execute(
        text(
            "CREATE TABLE steel_prices ("
            "id INTEGER PRIMARY KEY, year INTEGER, month INTEGER, "
            "location TEXT, grade TEXT, thickness NUMERIC)"
        )
    )
    session.commit()
    Base.metadata.create_all(
        bind=engine,
        tables=[LogicalRef.__table__, LogicalRefFilter.__table__],
    )
    ensure_logical_ref_seed(session)
    try:
        yield session
    finally:
        session.close()


def _part(db: Session, *, tailor: int = 0) -> None:
    db.execute(
        text(
            "INSERT INTO stamping_parts ("
            "id, location, material, thickness, effective_year, effective_month, "
            "expiry_year, expiry_month, is_tailor_welded, is_offal_nested, is_scrap_byproduct"
            ") VALUES (1, '芜湖', 'DC01', 1.5, 2024, 3, NULL, NULL, :tailor, 0, 0)"
        ),
        {"tailor": tailor},
    )
    db.commit()


def _price(db: Session, year: int, month: int, grade: str = "DC01") -> None:
    db.execute(
        text(
            "INSERT INTO steel_prices (year, month, location, grade, thickness) "
            "VALUES (:year, :month, '芜湖', :grade, 1.5)"
        ),
        {"year": year, "month": month, "grade": grade},
    )
    db.commit()


def test_part_material_before_effective_does_not_block(memory_db: Session) -> None:
    _part(memory_db)
    _price(memory_db, 2024, 2)
    ensure_logical_deletable(memory_db, "stamping_parts", [{"id": 1}], subject="该冲压零件")


def test_part_material_on_and_after_effective_blocks(memory_db: Session) -> None:
    _part(memory_db)
    _price(memory_db, 2024, 3)
    _price(memory_db, 2025, 12)
    with pytest.raises(BusinessException, match="钢材联动价") as caught:
        ensure_logical_deletable(memory_db, "stamping_parts", [{"id": 1}], subject="该冲压零件")
    assert "钢材联动价" in caught.value.message
    assert "2 条" in caught.value.message


def test_part_material_stops_before_first_change(memory_db: Session) -> None:
    _part(memory_db)
    memory_db.execute(
        text(
            "INSERT INTO stamping_part_material_changes "
            "(id, part_id, effective_year, effective_month, after_material) "
            "VALUES (10, 1, 2026, 1, 'DC03')"
        )
    )
    memory_db.commit()
    _price(memory_db, 2025, 12)
    with pytest.raises(BusinessException, match="钢材联动价"):
        ensure_logical_deletable(memory_db, "stamping_parts", [{"id": 1}])
    memory_db.execute(text("DELETE FROM steel_prices"))
    memory_db.commit()
    _price(memory_db, 2026, 1, grade="DC01")
    ensure_logical_deletable(memory_db, "stamping_parts", [{"id": 1}])


def test_january_cutoff_includes_prior_december(memory_db: Session) -> None:
    _part(memory_db)
    memory_db.execute(
        text(
            "INSERT INTO stamping_part_material_changes "
            "(id, part_id, effective_year, effective_month, after_material) "
            "VALUES (10, 1, 2025, 6, 'DC03'), (11, 1, 2026, 1, 'DC04')"
        )
    )
    memory_db.commit()
    _price(memory_db, 2025, 5, grade="DC03")
    ensure_logical_deletable(memory_db, "stamping_part_material_changes", [{"id": 10}])
    _price(memory_db, 2025, 12, grade="DC03")
    with pytest.raises(BusinessException, match="钢材联动价"):
        ensure_logical_deletable(memory_db, "stamping_part_material_changes", [{"id": 10}])
    memory_db.execute(text("DELETE FROM steel_prices"))
    memory_db.commit()
    _price(memory_db, 2026, 1, grade="DC03")
    ensure_logical_deletable(memory_db, "stamping_part_material_changes", [{"id": 10}])


def test_part_expiry_closes_window(memory_db: Session) -> None:
    _part(memory_db)
    memory_db.execute(
        text("UPDATE stamping_parts SET expiry_year = 2024, expiry_month = 6 WHERE id = 1")
    )
    memory_db.commit()
    _price(memory_db, 2024, 7)
    ensure_logical_deletable(memory_db, "stamping_parts", [{"id": 1}])
    memory_db.execute(text("DELETE FROM steel_prices"))
    memory_db.commit()
    _price(memory_db, 2024, 6)
    with pytest.raises(BusinessException, match="钢材联动价"):
        ensure_logical_deletable(memory_db, "stamping_parts", [{"id": 1}])


def test_change_uses_after_material_and_part_thickness(memory_db: Session) -> None:
    _part(memory_db)
    memory_db.execute(
        text(
            "INSERT INTO stamping_part_material_changes "
            "(id, part_id, effective_year, effective_month, after_material) "
            "VALUES (10, 1, 2025, 6, 'DC03')"
        )
    )
    memory_db.commit()
    _price(memory_db, 2025, 8, grade="DC01")
    ensure_logical_deletable(memory_db, "stamping_part_material_changes", [{"id": 10}])
    ensure_logical_deletable(memory_db, "stamping_parts", [{"id": 1}])
    memory_db.execute(text("DELETE FROM steel_prices"))
    memory_db.commit()
    memory_db.execute(
        text(
            "INSERT INTO steel_prices (year, month, location, grade, thickness) "
            "VALUES (2025, 8, '芜湖', 'DC03', 2.0)"
        )
    )
    memory_db.commit()
    ensure_logical_deletable(memory_db, "stamping_part_material_changes", [{"id": 10}])
    memory_db.execute(text("DELETE FROM steel_prices"))
    memory_db.commit()
    _price(memory_db, 2025, 8, grade="DC03")
    with pytest.raises(BusinessException, match="钢材联动价"):
        ensure_logical_deletable(memory_db, "stamping_part_material_changes", [{"id": 10}])


def test_change_outside_part_period_does_not_block(memory_db: Session) -> None:
    _part(memory_db)
    memory_db.execute(
        text("UPDATE stamping_parts SET expiry_year = 2025, expiry_month = 8 WHERE id = 1")
    )
    memory_db.execute(
        text(
            "INSERT INTO stamping_part_material_changes "
            "(id, part_id, effective_year, effective_month, after_material) "
            "VALUES (10, 1, 2025, 6, 'DC03')"
        )
    )
    memory_db.commit()
    _price(memory_db, 2025, 9, grade="DC03")
    ensure_logical_deletable(memory_db, "stamping_part_material_changes", [{"id": 10}])
    memory_db.execute(text("DELETE FROM steel_prices"))
    memory_db.commit()
    _price(memory_db, 2025, 8, grade="DC03")
    with pytest.raises(BusinessException, match="钢材联动价"):
        ensure_logical_deletable(memory_db, "stamping_part_material_changes", [{"id": 10}])


def test_other_location_and_numeric_thickness(memory_db: Session) -> None:
    _part(memory_db)
    memory_db.execute(
        text(
            "INSERT INTO steel_prices (year, month, location, grade, thickness) "
            "VALUES (2024, 3, '青岛', 'DC01', 1.5), (2024, 3, '芜湖', 'DC01', 1.5000)"
        )
    )
    memory_db.commit()
    with pytest.raises(BusinessException, match="钢材联动价") as caught:
        ensure_logical_deletable(memory_db, "stamping_parts", [{"id": 1}])
    assert "1 条" in caught.value.message


def test_seed_leaves_existing_configuration(memory_db: Session) -> None:
    memory_db.execute(
        text(
            "UPDATE logical_ref SET hint = '已改' "
            "WHERE deleted_table = 'stamping_parts' AND result_table = 'steel_prices'"
        )
    )
    memory_db.execute(
        text(
            "UPDATE logical_ref_filter SET compare = 'eq' "
            "WHERE deleted_table = 'stamping_parts' AND result_table = 'steel_prices' AND seq = 4"
        )
    )
    memory_db.execute(
        text(
            "INSERT INTO logical_ref (deleted_table, result_table, result_name, hint) "
            "VALUES ('stamping_parts', 'other_results', '别的结果', '请处理')"
        )
    )
    memory_db.commit()
    ensure_logical_ref_seed(memory_db)
    hint = memory_db.execute(
        text(
            "SELECT hint FROM logical_ref "
            "WHERE deleted_table = 'stamping_parts' AND result_table = 'steel_prices'"
        )
    ).scalar_one()
    compare = memory_db.execute(
        text(
            "SELECT compare FROM logical_ref_filter "
            "WHERE deleted_table = 'stamping_parts' AND result_table = 'steel_prices' AND seq = 4"
        )
    ).scalar_one()
    extra = memory_db.execute(
        text("SELECT result_name FROM logical_ref WHERE result_table = 'other_results'")
    ).scalar_one()
    assert hint == "已改"
    assert compare == "eq"
    assert extra == "别的结果"


def test_seed_has_only_the_steel_sample(memory_db: Session) -> None:
    rows = memory_db.execute(
        text("SELECT deleted_table, result_table FROM logical_ref ORDER BY deleted_table")
    ).all()
    assert rows == [
        ("stamping_part_material_changes", "steel_prices"),
        ("stamping_parts", "steel_prices"),
    ]


def _blocks(db: Session, table: str, row_id: int) -> bool:
    try:
        ensure_logical_deletable(db, table, [{"id": row_id}])
    except BusinessException as caught:
        assert "钢材联动价" in caught.message
        assert "核价 → 冲压钢材联动价 → 冲压钢材联动价一览" in caught.message
        return True
    return False


def test_part_window_month_by_month(memory_db: Session) -> None:
    """工艺材料：2024-03 起，到第一刀 2025-01 之前，零件失效 2024-08。"""
    _part(memory_db)
    memory_db.execute(
        text("UPDATE stamping_parts SET expiry_year = 2024, expiry_month = 8 WHERE id = 1")
    )
    memory_db.execute(
        text(
            "INSERT INTO stamping_part_material_changes "
            "(id, part_id, effective_year, effective_month, after_material) "
            "VALUES (10, 1, 2025, 1, 'DC03'), (11, 2, 2024, 4, 'DC03')"
        )
    )
    memory_db.commit()
    expected = {
        (2024, 2): False,
        (2024, 3): True,
        (2024, 8): True,
        (2024, 9): False,
        (2024, 12): False,
        (2025, 1): False,
    }
    for (year, month), should_block in expected.items():
        memory_db.execute(text("DELETE FROM steel_prices"))
        memory_db.commit()
        _price(memory_db, year, month)
        assert _blocks(memory_db, "stamping_parts", 1) is should_block, f"{year}-{month}"


def test_change_window_month_by_month(memory_db: Session) -> None:
    """第一刀 2024-06 到第二刀 2025-01 之前，且不超出零件 2024-03 至 2024-12。"""
    _part(memory_db)
    memory_db.execute(
        text("UPDATE stamping_parts SET expiry_year = 2024, expiry_month = 12 WHERE id = 1")
    )
    memory_db.execute(
        text(
            "INSERT INTO stamping_part_material_changes "
            "(id, part_id, effective_year, effective_month, after_material) "
            "VALUES (10, 1, 2024, 6, 'DC03'), (11, 1, 2025, 1, 'DC04'), "
            "(12, 2, 2024, 7, 'DC03')"
        )
    )
    memory_db.commit()
    expected = {
        (2024, 5): False,
        (2024, 6): True,
        (2024, 12): True,
        (2025, 1): False,
    }
    for (year, month), should_block in expected.items():
        memory_db.execute(text("DELETE FROM steel_prices"))
        memory_db.commit()
        _price(memory_db, year, month, grade="DC03")
        assert _blocks(memory_db, "stamping_part_material_changes", 10) is should_block


def test_open_ended_last_change_blocks_later_year(memory_db: Session) -> None:
    _part(memory_db)
    memory_db.execute(
        text(
            "INSERT INTO stamping_part_material_changes "
            "(id, part_id, effective_year, effective_month, after_material) "
            "VALUES (10, 1, 2024, 6, 'DC03')"
        )
    )
    memory_db.commit()
    _price(memory_db, 2027, 1, grade="DC03")
    assert _blocks(memory_db, "stamping_part_material_changes", 10)


def test_offal_and_scrap_skip_first_change(memory_db: Session) -> None:
    _part(memory_db)
    memory_db.execute(
        text(
            "UPDATE stamping_parts SET is_offal_nested = 1, "
            "expiry_year = 2024, expiry_month = 6 WHERE id = 1"
        )
    )
    memory_db.execute(
        text(
            "INSERT INTO stamping_part_material_changes "
            "(id, part_id, effective_year, effective_month, after_material) "
            "VALUES (10, 1, 2024, 4, 'DC03')"
        )
    )
    memory_db.commit()
    _price(memory_db, 2024, 5)
    assert _blocks(memory_db, "stamping_parts", 1)
    memory_db.execute(
        text("UPDATE stamping_parts SET is_offal_nested = 0, is_scrap_byproduct = 1 WHERE id = 1")
    )
    memory_db.commit()
    assert _blocks(memory_db, "stamping_parts", 1)


def test_service_delete_keeps_row_when_steel_price_hits(
    memory_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _part(memory_db)
    memory_db.execute(
        text(
            "INSERT INTO stamping_part_material_changes "
            "(id, part_id, effective_year, effective_month, after_material) "
            "VALUES (10, 1, 2024, 6, 'DC03')"
        )
    )
    memory_db.commit()
    _price(memory_db, 2024, 6, grade="DC03")
    deleted: list[int] = []
    monkeypatch.setattr(
        material_change_module._repo,
        "get_by_id",
        lambda _db, history_id: type("Row", (), {"id": history_id})() if history_id == 10 else None,
    )
    monkeypatch.setattr(
        material_change_module._repo,
        "delete",
        lambda _db, row: deleted.append(row.id),
    )
    with pytest.raises(BusinessException, match="钢材联动价"):
        StampingMaterialChangeService().delete(memory_db, [10])
    assert deleted == []
    memory_db.execute(text("DELETE FROM steel_prices"))
    memory_db.commit()
    StampingMaterialChangeService().delete(memory_db, [10])
    assert deleted == [10]


def test_tailor_weld_uses_part_expiry_not_first_change(memory_db: Session) -> None:
    _part(memory_db, tailor=1)
    memory_db.execute(
        text("UPDATE stamping_parts SET expiry_year = 2024, expiry_month = 6 WHERE id = 1")
    )
    memory_db.execute(
        text(
            "INSERT INTO stamping_part_material_changes "
            "(id, part_id, effective_year, effective_month, after_material) "
            "VALUES (10, 1, 2024, 4, 'DC03')"
        )
    )
    memory_db.commit()
    _price(memory_db, 2024, 5)
    with pytest.raises(BusinessException, match="钢材联动价"):
        ensure_logical_deletable(memory_db, "stamping_parts", [{"id": 1}])
    memory_db.execute(text("DELETE FROM steel_prices"))
    memory_db.commit()
    _price(memory_db, 2024, 7)
    ensure_logical_deletable(memory_db, "stamping_parts", [{"id": 1}])
