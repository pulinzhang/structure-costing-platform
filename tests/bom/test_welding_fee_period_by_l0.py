"""焊接费取件：年交集以 L0 树根为准，不认 L1 本行生失效。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.bom import (
    BomNode,
    BomSnapshot,
    BomWeldingProcessBreakdownLine,
    BomWeldingProcessBreakdownNode,
)
from app.models.masterdata.location import Location
from app.models.masterdata.vehicle_model import VehicleModel
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)

LOCATION = "青岛"
VEHICLE_MODEL = "T28"
BOM_VERSION = "D/09"


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
            VehicleModel.__table__,
            BomSnapshot.__table__,
            BomNode.__table__,
            BomWeldingProcessBreakdownNode.__table__,
            BomWeldingProcessBreakdownLine.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
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
            vehicle_model=VEHICLE_MODEL,
            effective_year=2020,
            effective_month=1,
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


def _snapshot(db: Session) -> BomSnapshot:
    row = BomSnapshot(
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=BOM_VERSION,
        stage="initial",
        status="active",
        source_filename="bom.xlsx",
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _bom_node(
    db: Session,
    snapshot: BomSnapshot,
    *,
    level: int,
    part_number: str,
    parent_id: int | None = None,
    effective_year: int,
    effective_month: int,
    expiry_year: int | None,
    expiry_month: int | None,
) -> BomNode:
    row = BomNode(
        snapshot_id=snapshot.id,
        parent_id=parent_id,
        level=level,
        seq_no=1 if level == 0 else None,
        part_number=part_number,
        part_name=part_number,
        node_role="supply" if level == 0 else "make",
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=snapshot.bom_version,
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _breakdown(
    db: Session,
    *,
    source: BomNode,
    level: int,
    part_number: str,
) -> BomWeldingProcessBreakdownNode:
    row = BomWeldingProcessBreakdownNode(
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=BOM_VERSION,
        snapshot_id=source.snapshot_id,
        source_node_id=source.id,
        part_number=part_number,
        part_name=part_number,
        level=level,
        node_role="supply" if level == 0 else "structure",
        assembly_qty=Decimal("1"),
        weld_info_raw="点焊：1",
        parse_status="ok",
        process_line_count=1,
        audit_status="pending",
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_list_overlapping_year_uses_l0_not_l1_open_expiry(memory_db: Session) -> None:
    """树根已截断到上年，L1 失效空：整棵（含 L1）不得进该年账。"""
    snapshot = _snapshot(memory_db)
    l0 = _bom_node(
        memory_db,
        snapshot,
        level=0,
        part_number="ROOT-AA",
        effective_year=2020,
        effective_month=1,
        expiry_year=2025,
        expiry_month=12,
    )
    l1 = _bom_node(
        memory_db,
        snapshot,
        level=1,
        part_number="CHILD-AA",
        parent_id=l0.id,
        effective_year=2020,
        effective_month=1,
        expiry_year=None,
        expiry_month=None,
    )
    _breakdown(memory_db, source=l0, level=0, part_number="ROOT-AA")
    _breakdown(memory_db, source=l1, level=1, part_number="CHILD-AA")

    rows = BomWeldingProcessBreakdownRepository().list_overlapping_year(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        year=2026,
    )
    assert rows == []


def test_list_overlapping_year_includes_tree_when_l0_overlaps(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    l0 = _bom_node(
        memory_db,
        snapshot,
        level=0,
        part_number="ROOT-AB",
        effective_year=2026,
        effective_month=8,
        expiry_year=None,
        expiry_month=None,
    )
    l1 = _bom_node(
        memory_db,
        snapshot,
        level=1,
        part_number="CHILD-AB",
        parent_id=l0.id,
        effective_year=2026,
        effective_month=8,
        expiry_year=None,
        expiry_month=None,
    )
    root_bd = _breakdown(memory_db, source=l0, level=0, part_number="ROOT-AB")
    child_bd = _breakdown(memory_db, source=l1, level=1, part_number="CHILD-AB")

    rows = BomWeldingProcessBreakdownRepository().list_overlapping_year(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        year=2026,
    )
    assert {row.id for row in rows} == {root_bd.id, child_bd.id}
