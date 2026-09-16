"""零件用在哪：匹配、路径连乘、上限。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.exceptions.base import BusinessException
from app.models.bom.node import BomNode, BomSnapshot
from app.schemas.dto.bom_where_used_dto import BomWhereUsedQuery
from app.services.bom.where_used.service import BomWhereUsedService

LOCATION = "芜湖"
VEHICLE_MODEL = "T13J"
BOM_VERSION = "D/09"


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[BomSnapshot.__table__, BomNode.__table__])
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _snapshot(db: Session, *, status: str = "active") -> BomSnapshot:
    row = BomSnapshot(
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=BOM_VERSION,
        stage="mass",
        status=status,
        source_filename="fixture.xlsx",
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _node(
    db: Session,
    snapshot: BomSnapshot,
    *,
    level: int,
    part_number: str,
    parent: BomNode | None = None,
    qty: Decimal | None = Decimal("1"),
    qty_unit: str = "pcs",
    part_name: str | None = None,
    node_role: str = "make",
    is_supply_unit: bool = False,
) -> BomNode:
    row = BomNode(
        snapshot_id=snapshot.id,
        parent_id=parent.id if parent else None,
        level=level,
        part_number=part_number,
        part_name=part_name,
        qty=qty,
        qty_unit=qty_unit,
        node_role="supply" if level == 0 else node_role,
        is_supply_unit=is_supply_unit or level == 0,
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _search(db: Session, raw: str, **kwargs: object) -> object:
    payload = {"query": raw, **kwargs}
    return BomWhereUsedService().search(db, BomWhereUsedQuery.model_validate(payload))


def test_full_number_and_short_code_same_hits(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    l0 = _node(memory_db, snapshot, level=0, part_number="551000001AA", part_name="总成")
    _node(
        memory_db,
        snapshot,
        level=1,
        part_number="551001137AA",
        part_name="左后门上铰链安装板总成",
        parent=l0,
    )
    by_full = _search(memory_db, "551001137AA")
    by_short = _search(memory_db, "1137")
    assert by_full.summary.hit_count == 1
    assert by_short.summary.hit_count == 1
    assert by_full.paths[0].l0_part_number == "551000001AA"
    assert by_short.paths[0].nodes[0].part_number == "551001137AA"


def test_middle_four_digits_not_short_code(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    l0 = _node(memory_db, snapshot, level=0, part_number="500000001AA")
    _node(memory_db, snapshot, level=1, part_number="551113700AA", parent=l0)
    result = _search(memory_db, "1137")
    assert result.summary.hit_count == 0


def test_year_token_rejected(memory_db: Session) -> None:
    with pytest.raises(BusinessException, match="不是零件短码"):
        _search(memory_db, "2026")


def test_single_char_name_rejected(memory_db: Session) -> None:
    with pytest.raises(BusinessException, match="至少输入 2 个字"):
        _search(memory_db, "板")


def test_name_like(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    l0 = _node(memory_db, snapshot, level=0, part_number="500000002AA")
    _node(
        memory_db,
        snapshot,
        level=1,
        part_number="551001137AA",
        part_name="左后门上铰链安装板总成",
        parent=l0,
    )
    result = _search(memory_db, "铰链")
    assert result.summary.hit_count == 1


def test_missing_part_empty(memory_db: Session) -> None:
    _snapshot(memory_db)
    result = _search(memory_db, "ZZZNOHIT99")
    assert result.summary.hit_count == 0
    assert result.paths == []


def test_l0_self_path_length(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    _node(memory_db, snapshot, level=0, part_number="551000099AA", part_name="供货总成")
    result = _search(memory_db, "551000099AA")
    assert len(result.paths) == 1
    assert len(result.paths[0].nodes) == 1
    assert result.paths[0].l0_part_number == "551000099AA"


def test_two_hangs_same_l0_sum_qty(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    l0 = _node(memory_db, snapshot, level=0, part_number="551000010AA")
    _node(
        memory_db,
        snapshot,
        level=1,
        part_number="551001137AA",
        parent=l0,
        qty=Decimal("1"),
    )
    _node(
        memory_db,
        snapshot,
        level=1,
        part_number="551001137AA",
        parent=l0,
        qty=Decimal("2"),
    )
    result = _search(memory_db, "551001137AA")
    assert result.summary.hit_count == 2
    assert sum((path.path_qty for path in result.paths), Decimal("0")) == Decimal("3")


def test_mixed_qty_unit(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    l0 = _node(memory_db, snapshot, level=0, part_number="551000011AA")
    _node(
        memory_db,
        snapshot,
        level=1,
        part_number="B11-4102613",
        parent=l0,
        qty=Decimal("1"),
        qty_unit="pcs",
    )
    _node(
        memory_db,
        snapshot,
        level=1,
        part_number="B11-4102613",
        parent=l0,
        qty=Decimal("10"),
        qty_unit="mm",
    )
    result = _search(memory_db, "B11-4102613")
    assert result.summary.hit_count == 2
    assert {path.path_qty for path in result.paths} == {Decimal("1"), Decimal("10")}


def test_hit_limit_409(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    for index in range(2001):
        memory_db.add(
            BomNode(
                snapshot_id=snapshot.id,
                level=0,
                part_number="OVERFLOW0001AA",
                part_name=f"总成{index}",
                node_role="supply",
                is_supply_unit=True,
                created_by="system",
                updated_by="system",
            )
        )
    memory_db.commit()
    with pytest.raises(BusinessException) as raised:
        _search(memory_db, "OVERFLOW0001AA")
    assert raised.value.code == 409
