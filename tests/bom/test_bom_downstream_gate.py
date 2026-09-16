"""材料清单直接下游门闩：采购对象、焊接拆解拦删除；子孙不拦。"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.exceptions.base import BusinessException
from app.models.bom.node import BomNode, BomSnapshot
from app.models.bom.procurement_object import (
    BomProcurementObject,
    BomProcurementObjectList,
)
from app.models.bom.welding_fee import BomWeldingFee
from app.models.bom.welding_process_breakdown import BomWeldingProcessBreakdownNode
from app.models.costing.assembly_cost import AssemblyCost
from app.models.masterdata.location import Location
from app.models.masterdata.supplier import Supplier
from app.models.masterdata.vehicle_model import VehicleModel
from app.services.bom.bom_service import BomService

LOCATION = "青岛"
VEHICLE_MODEL = "T28"
BOM_VERSION = "D/00"


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
            Supplier.__table__,
            BomSnapshot.__table__,
            BomNode.__table__,
            BomProcurementObjectList.__table__,
            BomProcurementObject.__table__,
            BomWeldingProcessBreakdownNode.__table__,
            BomWeldingFee.__table__,
            AssemblyCost.__table__,
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


def _add_snapshot(db: Session) -> BomSnapshot:
    row = BomSnapshot(
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=BOM_VERSION,
        stage="initial",
        status="active",
        source_filename="fixture-bom.xlsx",
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _add_node(db: Session, snapshot: BomSnapshot) -> BomNode:
    node = BomNode(
        snapshot_id=snapshot.id,
        level=0,
        part_number="501006870AA",
        node_role="supply",
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=BOM_VERSION,
        effective_year=2020,
        effective_month=1,
        created_by="system",
        updated_by="system",
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


class TestBomDownstreamGate:
    def test_delete_snapshot_without_direct_downstream(self, memory_db: Session) -> None:
        snapshot = _add_snapshot(memory_db)
        BomService().delete_snapshot(memory_db, snapshot.id)
        assert memory_db.get(BomSnapshot, snapshot.id) is None

    def test_delete_snapshot_blocked_by_procurement_then_ok(self, memory_db: Session) -> None:
        snapshot = _add_snapshot(memory_db)
        head = BomProcurementObjectList(
            snapshot_id=snapshot.id,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version=BOM_VERSION,
            source_filename="fixture-bom.xlsx",
            generated_at=datetime(2026, 1, 1),
            created_by="system",
            updated_by="system",
        )
        memory_db.add(head)
        memory_db.commit()

        with pytest.raises(BusinessException) as caught:
            BomService().delete_snapshot(memory_db, snapshot.id)
        assert caught.value.code == 409
        assert "采购对象清单" in caught.value.message
        assert "焊接工艺拆解" not in caught.value.message

        memory_db.delete(head)
        memory_db.commit()
        BomService().delete_snapshot(memory_db, snapshot.id)
        assert memory_db.get(BomSnapshot, snapshot.id) is None

    def test_delete_snapshot_blocked_by_welding_breakdown(self, memory_db: Session) -> None:
        snapshot = _add_snapshot(memory_db)
        memory_db.add(
            BomWeldingProcessBreakdownNode(
                location=LOCATION,
                vehicle_model=VEHICLE_MODEL,
                bom_version=BOM_VERSION,
                snapshot_id=snapshot.id,
                source_node_id=1,
                part_number="501006870AA",
                level=0,
                node_role="supply",
                assembly_qty=Decimal("1"),
                weld_info_raw="焊点 2",
                created_by="system",
                updated_by="system",
            )
        )
        memory_db.commit()

        with pytest.raises(BusinessException) as caught:
            BomService().delete_snapshot(memory_db, snapshot.id)
        assert caught.value.code == 409
        assert "焊接工艺拆解" in caught.value.message

    def test_grandchildren_do_not_block(self, memory_db: Session) -> None:
        snapshot = _add_snapshot(memory_db)
        memory_db.add(
            BomWeldingFee(
                year=2026,
                location=LOCATION,
                vehicle_model=VEHICLE_MODEL,
                bom_version=BOM_VERSION,
                part_number="501006870AA",
                created_by="system",
                updated_by="system",
            )
        )
        memory_db.add(
            AssemblyCost(
                year=2026,
                month=1,
                location=LOCATION,
                vehicle_model=VEHICLE_MODEL,
                bom_version=BOM_VERSION,
                source_node_id=1,
                part_number="501006870AA",
                created_by="system",
                updated_by="system",
            )
        )
        memory_db.commit()

        BomService().assert_bom_scope_unused(
            memory_db,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version=BOM_VERSION,
            action="覆盖导入",
        )
        BomService().delete_snapshot(memory_db, snapshot.id)
        assert memory_db.get(BomSnapshot, snapshot.id) is None

    def test_delete_node_blocked_by_procurement(self, memory_db: Session) -> None:
        snapshot = _add_snapshot(memory_db)
        node = _add_node(memory_db, snapshot)
        memory_db.add(
            BomProcurementObjectList(
                snapshot_id=snapshot.id,
                location=LOCATION,
                vehicle_model=VEHICLE_MODEL,
                bom_version=BOM_VERSION,
                source_filename="fixture-bom.xlsx",
                generated_at=datetime(2026, 1, 1),
                created_by="system",
                updated_by="system",
            )
        )
        memory_db.commit()

        with pytest.raises(BusinessException) as caught:
            BomService().delete_node(memory_db, node.id)
        assert caught.value.code == 409
        assert memory_db.get(BomNode, node.id) is not None
