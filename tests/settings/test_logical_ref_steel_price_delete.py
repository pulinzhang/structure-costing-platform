"""删钢材联动价：零件价格抄过该行则整条/整批都不删。"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.database import Base
from app.exceptions.base import BusinessException
from app.models.costing import SteelPrice
from app.models.settings.logical_ref.model import LogicalRef, LogicalRefFilter
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.schemas.dto.steel_price_dto import SteelPriceBatchDeleteDTO
from app.services.costing.steel_price.crud import batch_delete_steel_prices, delete_steel_price
from app.services.costing.steel_price.logical_ref_seed import (
    ensure as ensure_steel_price_logical_ref,
)
from app.services.settings.logical_ref.service import ensure_logical_deletable

_HINT = "请到「核价 → 冲压零件价格核算 → 冲压零件价格一览」处理"


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session = sessionmaker(bind=engine)()
    session.execute(
        text("CREATE TABLE stamping_part_costs (id INTEGER PRIMARY KEY, steel_price_id INTEGER)")
    )
    session.commit()
    Base.metadata.create_all(
        bind=engine,
        tables=[SteelPrice.__table__, LogicalRef.__table__, LogicalRefFilter.__table__],
    )
    ensure_steel_price_logical_ref(session)
    try:
        yield session
    finally:
        session.close()


def _price(
    db: Session,
    *,
    price_id: int,
    mill: str = "马钢",
    grade: str = "DC01",
    audit_status: str = AUDIT_PENDING,
    year: int = 2024,
    month: int = 3,
    location: str = "芜湖",
    category_name: str = "冷轧",
) -> None:
    db.add(
        SteelPrice(
            id=price_id,
            year=year,
            month=month,
            location=location,
            steel_mill=mill,
            category_name=category_name,
            grade=grade,
            thickness=Decimal("1.5000"),
            width=Decimal("1250"),
            base_price=Decimal("4000"),
            final_price_per_ton=Decimal("4000"),
            calc_batch_id="strict",
            match_status="manual",
            calculated_at=datetime(2024, 3, 1),
            audit_status=audit_status,
        )
    )
    db.commit()


def _cost(db: Session, cost_id: int, steel_price_id: int | None) -> None:
    db.execute(
        text("INSERT INTO stamping_part_costs (id, steel_price_id) VALUES (:id, :steel_price_id)"),
        {"id": cost_id, "steel_price_id": steel_price_id},
    )
    db.commit()


def _remaining(db: Session) -> list[int]:
    rows = db.execute(text("SELECT id FROM steel_prices ORDER BY id")).all()
    return [int(row[0]) for row in rows]


def test_seed_filter_is_pointer_equality(memory_db: Session) -> None:
    head = memory_db.execute(
        text(
            "SELECT result_name, hint FROM logical_ref "
            "WHERE deleted_table = 'steel_prices' AND result_table = 'stamping_part_costs'"
        )
    ).one()
    filters = memory_db.execute(
        text(
            "SELECT seq, compare, result_column, value_column, value_table "
            "FROM logical_ref_filter "
            "WHERE deleted_table = 'steel_prices' AND result_table = 'stamping_part_costs' "
            "ORDER BY seq"
        )
    ).all()
    assert head == ("冲压零件价格", _HINT)
    assert filters == [(1, "eq", "steel_price_id", "id", None)]


def test_null_and_other_id_do_not_block_delete(memory_db: Session) -> None:
    _price(memory_db, price_id=7)
    _cost(memory_db, 1, None)
    _cost(memory_db, 2, 8)
    delete_steel_price(SteelPriceRepository(), memory_db, 7)
    assert _remaining(memory_db) == []


def test_copied_pointer_keeps_the_row_and_counts_copies(memory_db: Session) -> None:
    _price(memory_db, price_id=7)
    _cost(memory_db, 1, 7)
    _cost(memory_db, 2, 7)
    _cost(memory_db, 3, None)
    _cost(memory_db, 4, 9)
    with pytest.raises(BusinessException, match="冲压零件价格") as caught:
        delete_steel_price(SteelPriceRepository(), memory_db, 7)
    message = caught.value.message
    assert "无法删除该钢材联动价" in message
    assert "有 2 条冲压零件价格" in message
    assert _HINT in message
    assert "请处理完以上数据后再删除。" in message
    assert caught.value.audit_detail is None
    assert _remaining(memory_db) == [7]
    memory_db.execute(
        text("UPDATE stamping_part_costs SET steel_price_id = NULL WHERE steel_price_id = 7")
    )
    memory_db.commit()
    delete_steel_price(SteelPriceRepository(), memory_db, 7)
    assert _remaining(memory_db) == []


def test_one_copied_id_blocks_the_whole_batch(memory_db: Session) -> None:
    _price(memory_db, price_id=7, mill="马钢")
    _price(memory_db, price_id=8, mill="首钢", audit_status=AUDIT_REJECTED)
    _price(memory_db, price_id=9, mill="唐钢", audit_status=AUDIT_APPROVED)
    _cost(memory_db, 1, 8)
    _cost(memory_db, 2, None)
    repository = SteelPriceRepository()
    assert repository.list_unaudited_ids(memory_db, year=2024, month=3, location="芜湖") == [7, 8]
    with pytest.raises(BusinessException, match="1 条冲压零件价格"):
        batch_delete_steel_prices(
            repository,
            memory_db,
            SteelPriceBatchDeleteDTO(year=2024, month=3, location="芜湖"),
        )
    assert _remaining(memory_db) == [7, 8, 9]
    memory_db.execute(text("UPDATE stamping_part_costs SET steel_price_id = NULL WHERE id = 1"))
    memory_db.commit()
    result = batch_delete_steel_prices(
        repository,
        memory_db,
        SteelPriceBatchDeleteDTO(year=2024, month=3, location="芜湖"),
    )
    assert result.deleted_count == 2
    assert result.skipped_approved_count == 1
    assert _remaining(memory_db) == [9]


def test_batch_filters_ignore_copies_outside_the_condition(memory_db: Session) -> None:
    _price(memory_db, price_id=7, grade="DC01")
    _price(memory_db, price_id=8, mill="首钢", grade="DC04")
    _price(memory_db, price_id=11, mill="宝钢", location="青岛")
    _cost(memory_db, 1, 8)
    _cost(memory_db, 2, 11)
    repository = SteelPriceRepository()
    assert repository.list_unaudited_ids(
        memory_db, year=2024, month=3, location="芜湖", grade="DC01"
    ) == [7]
    result = batch_delete_steel_prices(
        repository,
        memory_db,
        SteelPriceBatchDeleteDTO(year=2024, month=3, location="芜湖", grade="DC01"),
    )
    assert result.deleted_count == 1
    assert _remaining(memory_db) == [8, 11]


def test_empty_unaudited_set_does_not_block(memory_db: Session) -> None:
    _price(memory_db, price_id=9, audit_status=AUDIT_APPROVED)
    _cost(memory_db, 1, 9)
    result = batch_delete_steel_prices(
        SteelPriceRepository(),
        memory_db,
        SteelPriceBatchDeleteDTO(year=2024, month=3, location="芜湖"),
    )
    assert result.deleted_count == 0
    assert result.skipped_approved_count == 1
    assert _remaining(memory_db) == [9]


def test_two_keys_count_only_matching_copies(memory_db: Session) -> None:
    _price(memory_db, price_id=7, mill="马钢")
    _price(memory_db, price_id=8, mill="首钢")
    _price(memory_db, price_id=9, mill="唐钢")
    _cost(memory_db, 1, 7)
    _cost(memory_db, 2, 7)
    _cost(memory_db, 3, 8)
    ensure_logical_deletable(memory_db, "steel_prices", [{"id": 9}])
    with pytest.raises(BusinessException, match="3 条冲压零件价格"):
        ensure_logical_deletable(memory_db, "steel_prices", [{"id": 7}, {"id": 8}, {"id": 9}])
    ensure_logical_deletable(memory_db, "steel_prices", [])
