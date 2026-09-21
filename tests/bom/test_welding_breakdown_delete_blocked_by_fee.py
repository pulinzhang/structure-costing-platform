"""焊接工艺拆解删除：焊接费 source_breakdown_node_id RESTRICT。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.exceptions.base import BusinessException
from app.models.bom import BomNode, BomSnapshot
from app.models.bom.welding_fee import BomWeldingFee
from app.models.bom.welding_fee_item import BomWeldingFeeItem
from app.models.bom.welding_process_breakdown import (
    BomWeldingProcessBreakdownLine,
    BomWeldingProcessBreakdownNode,
)
from app.models.masterdata.location import Location
from app.models.masterdata.vehicle_model import VehicleModel
from app.services.bom.welding_process_breakdown.audit_service import WELDING_FEE_REFERENCED
from app.services.bom.welding_process_breakdown.service import BomWeldingProcessBreakdownService

LOCATION = "青岛"
VEHICLE = "T28"
BOM_VERSION = "D/00"
PART_NUMBER = "501006870AA"


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
            BomWeldingFee.__table__,
            BomWeldingFeeItem.__table__,
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
            vehicle_model=VEHICLE,
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


def _add_breakdown(db: Session) -> BomWeldingProcessBreakdownNode:
    snapshot = BomSnapshot(
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version=BOM_VERSION,
        stage="initial",
        status="active",
        source_filename="bom.xlsx",
        created_by="system",
        updated_by="system",
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    source = BomNode(
        snapshot_id=snapshot.id,
        parent_id=None,
        level=0,
        seq_no=1,
        part_number=PART_NUMBER,
        part_name=PART_NUMBER,
        node_role="supply",
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version=BOM_VERSION,
        effective_year=2020,
        effective_month=1,
        created_by="system",
        updated_by="system",
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    node = BomWeldingProcessBreakdownNode(
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version=BOM_VERSION,
        snapshot_id=snapshot.id,
        source_node_id=source.id,
        part_number=PART_NUMBER,
        level=0,
        node_role="supply",
        supply_part_number=PART_NUMBER,
        assembly_qty=Decimal("1"),
        weld_info_raw="焊点 2",
        created_by="system",
        updated_by="system",
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def _add_fee(db: Session, node: BomWeldingProcessBreakdownNode) -> BomWeldingFee:
    fee = BomWeldingFee(
        year=2026,
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version=BOM_VERSION,
        source_breakdown_node_id=node.id,
        part_number=PART_NUMBER,
        created_by="system",
        updated_by="system",
    )
    db.add(fee)
    db.commit()
    db.refresh(fee)
    return fee


def _node_exists(db: Session, node_id: int) -> bool:
    return (
        db.query(BomWeldingProcessBreakdownNode)
        .filter(BomWeldingProcessBreakdownNode.id == node_id)
        .first()
        is not None
    )


def test_batch_delete_breakdown_without_fee(memory_db: Session) -> None:
    node = _add_breakdown(memory_db)
    node_id = node.id
    result = BomWeldingProcessBreakdownService().batch_delete(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version=BOM_VERSION,
    )
    assert result.deleted_count == 1
    assert not _node_exists(memory_db, node_id)


def test_batch_delete_blocked_when_welding_fee_exists(memory_db: Session) -> None:
    node = _add_breakdown(memory_db)
    node_id = node.id
    fee = _add_fee(memory_db, node)

    with pytest.raises(BusinessException, match=WELDING_FEE_REFERENCED):
        BomWeldingProcessBreakdownService().batch_delete(
            memory_db,
            location=LOCATION,
            vehicle_model=VEHICLE,
            bom_version=BOM_VERSION,
        )

    assert _node_exists(memory_db, node_id)
    memory_db.delete(fee)
    memory_db.commit()
    BomWeldingProcessBreakdownService().batch_delete(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version=BOM_VERSION,
    )
    assert not _node_exists(memory_db, node_id)
