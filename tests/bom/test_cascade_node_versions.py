"""BOM cascade 版本口径：只对 L0 节点 bom_version 去重。"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.bom import BomNode, BomSnapshot
from app.repositories.bom.bom.snapshot import BomSnapshotRepository

LOCATION = "芜湖"
VEHICLE_MODEL = "T13J"


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
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    Base.metadata.create_all(
        bind=engine,
        tables=[BomSnapshot.__table__, BomNode.__table__],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_snapshot_with_ec_node(db: Session) -> None:
    snapshot = BomSnapshot(
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version="D/09",
        stage="mass",
        status="active",
        source_filename="seed.xlsx",
        created_by="system",
        updated_by="system",
    )
    db.add(snapshot)
    db.flush()
    db.add(
        BomNode(
            snapshot_id=snapshot.id,
            parent_id=None,
            level=0,
            sort_no=0,
            seq_no=1,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version="D/09",
            effective_year=2025,
            effective_month=1,
            expiry_year=2025,
            expiry_month=4,
            part_number="551003085AA",
            part_name="旧总成",
            node_role="supply",
            is_supply_unit=True,
            created_by="system",
            updated_by="system",
        )
    )
    db.add(
        BomNode(
            snapshot_id=snapshot.id,
            parent_id=None,
            level=0,
            sort_no=1,
            seq_no=1,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version="EC-202505",
            effective_year=2025,
            effective_month=5,
            part_number="551003085AB",
            part_name="新总成",
            node_role="supply",
            is_supply_unit=True,
            created_by="system",
            updated_by="system",
        )
    )
    db.commit()


def test_cascade_bom_versions_from_l0_nodes_only(memory_db: Session) -> None:
    _seed_snapshot_with_ec_node(memory_db)
    options = BomSnapshotRepository().get_cascade_filter_options(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
    )
    assert options["bom_versions"] == ["EC-202505", "D/09"]


def test_cascade_bom_versions_as_of_month_uses_l0_hit(
    memory_db: Session,
) -> None:
    _seed_snapshot_with_ec_node(memory_db)
    april = BomSnapshotRepository().get_cascade_filter_options(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        as_of_year=2025,
        as_of_month=4,
    )
    assert april["bom_versions"] == ["D/09"]

    may = BomSnapshotRepository().get_cascade_filter_options(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        as_of_year=2025,
        as_of_month=5,
    )
    assert may["bom_versions"] == ["EC-202505"]


def test_cascade_version_source_snapshot_excludes_l0_ec_words(memory_db: Session) -> None:
    """生成页：version_source=snapshot 只列头字，不出 EC-*。"""
    _seed_snapshot_with_ec_node(memory_db)
    options = BomSnapshotRepository().get_cascade_filter_options(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        version_source="snapshot",
    )
    assert options["bom_versions"] == ["D/09"]
