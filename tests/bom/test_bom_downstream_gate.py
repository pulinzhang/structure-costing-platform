"""材料清单删除：子表外键拒绝时不点名；采购清单随 snapshot 级联，拆解 snapshot_id 只是辅助指针。"""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
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
from app.models.engineering_change.design_change.change_order import EngineeringChangeOrder
from app.models.engineering_change.design_change.upload_log import EngineeringChangeUploadLog
from app.models.file_trace.upload_file import UploadFile
from app.models.masterdata.location import Location
from app.models.masterdata.supplier import Supplier
from app.models.masterdata.vehicle_model import VehicleModel
from app.services.bom.bom.node import BomNodeService
from app.services.bom.bom.snapshot import BomSnapshotService

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
            UploadFile.__table__,
            BomSnapshot.__table__,
            BomNode.__table__,
            BomProcurementObjectList.__table__,
            BomProcurementObject.__table__,
            BomWeldingProcessBreakdownNode.__table__,
            BomWeldingFee.__table__,
            AssemblyCost.__table__,
            EngineeringChangeUploadLog.__table__,
            EngineeringChangeOrder.__table__,
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
        BomSnapshotService().delete_snapshot(memory_db, snapshot.id)
        assert memory_db.get(BomSnapshot, snapshot.id) is None

    def test_delete_snapshot_cascades_procurement_list(self, memory_db: Session) -> None:
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
        snapshot_id = snapshot.id
        head_id = head.id

        BomSnapshotService().delete_snapshot(memory_db, snapshot_id)
        memory_db.expire_all()
        assert memory_db.get(BomSnapshot, snapshot_id) is None
        assert memory_db.get(BomProcurementObjectList, head_id) is None

    def test_delete_snapshot_leaves_auxiliary_breakdown_pointer(self, memory_db: Session) -> None:
        snapshot = _add_snapshot(memory_db)
        node = BomWeldingProcessBreakdownNode(
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
        memory_db.add(node)
        memory_db.commit()
        snapshot_id = snapshot.id
        node_id = node.id

        BomSnapshotService().delete_snapshot(memory_db, snapshot_id)
        memory_db.expire_all()
        assert memory_db.get(BomSnapshot, snapshot_id) is None
        left = memory_db.get(BomWeldingProcessBreakdownNode, node_id)
        assert left is not None
        assert left.snapshot_id == snapshot_id

    def test_delete_snapshot_blocked_by_engineering_change_order(self, memory_db: Session) -> None:
        """变更单 before_assembly_node_id RESTRICT：有单则不能删；清表后可删。"""
        snapshot = _add_snapshot(memory_db)
        node = _add_node(memory_db, snapshot)
        memory_db.add(
            UploadFile(
                file_category="engineering_change",
                original_filename="ec.xlsx",
                stored_relpath="engineering-change/ec.xlsx",
                file_hash="b" * 64,
                file_size=10,
                extension=".xlsx",
                created_by="system",
                updated_by="system",
            )
        )
        memory_db.flush()
        upload_file_id = memory_db.query(UploadFile).one().id
        log_row = EngineeringChangeUploadLog(
            upload_file_id=upload_file_id,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            customer_name="奇瑞",
            effective_year=2025,
            effective_month=7,
            original_filename="ec.xlsx",
            status="success",
            created_by="system",
            updated_by="system",
        )
        memory_db.add(log_row)
        memory_db.flush()
        memory_db.add(
            EngineeringChangeOrder(
                upload_log_id=log_row.id,
                upload_file_id=upload_file_id,
                before_assembly_node_id=node.id,
                excel_row=2,
                project_code=VEHICLE_MODEL,
                effective_period_text="2025年07月",
                change_type="完成停止",
                before_assembly_part_number=node.part_number,
                part_level="总成",
                status="active",
                created_by="system",
                updated_by="system",
            )
        )
        memory_db.commit()

        with pytest.raises(BusinessException) as caught:
            BomSnapshotService().delete_snapshot(memory_db, snapshot.id)
        assert "仍被引用，不能删除" in caught.value.message
        assert "工程变更" not in caught.value.message
        assert "总成核价" not in caught.value.message
        assert memory_db.get(BomSnapshot, snapshot.id) is not None

        memory_db.query(EngineeringChangeOrder).delete()
        memory_db.query(EngineeringChangeUploadLog).delete()
        memory_db.commit()
        BomSnapshotService().delete_snapshot(memory_db, snapshot.id)
        assert memory_db.get(BomSnapshot, snapshot.id) is None

    def test_grandchildren_do_not_block(self, memory_db: Session) -> None:
        """应用预检不读总成核价。真正删除时外键拒绝，文案不点名核价。"""
        snapshot = _add_snapshot(memory_db)
        node = _add_node(memory_db, snapshot)
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
        cost = AssemblyCost(
            year=2026,
            month=1,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version=BOM_VERSION,
            source_node_id=node.id,
            part_number="501006870AA",
            created_by="system",
            updated_by="system",
        )
        memory_db.add(cost)
        memory_db.commit()

        with pytest.raises(BusinessException) as caught:
            BomSnapshotService().delete_snapshot(memory_db, snapshot.id)
        assert "仍被引用，不能删除" in caught.value.message
        assert "总成核价" not in caught.value.message
        assert "工程变更" not in caught.value.message
        assert "反审核" not in caught.value.message
        assert memory_db.get(BomSnapshot, snapshot.id) is not None

        memory_db.query(AssemblyCost).filter(AssemblyCost.id == cost.id).delete()
        memory_db.commit()
        BomSnapshotService().delete_snapshot(memory_db, snapshot.id)
        assert memory_db.get(BomSnapshot, snapshot.id) is None

    def test_delete_snapshot_blocked_by_cost_and_change_order(self, memory_db: Session) -> None:
        snapshot = _add_snapshot(memory_db)
        node = _add_node(memory_db, snapshot)
        memory_db.add(
            AssemblyCost(
                year=2025,
                month=4,
                location=LOCATION,
                vehicle_model=VEHICLE_MODEL,
                bom_version=BOM_VERSION,
                source_node_id=node.id,
                part_number=node.part_number,
                created_by="system",
                updated_by="system",
            )
        )
        memory_db.add(
            UploadFile(
                file_category="engineering_change",
                original_filename="both.xlsx",
                stored_relpath="engineering-change/both.xlsx",
                file_hash="c" * 64,
                file_size=10,
                extension=".xlsx",
                created_by="system",
                updated_by="system",
            )
        )
        memory_db.flush()
        upload_file_id = memory_db.query(UploadFile).one().id
        log_row = EngineeringChangeUploadLog(
            upload_file_id=upload_file_id,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            customer_name="奇瑞",
            effective_year=2025,
            effective_month=7,
            original_filename="both.xlsx",
            status="success",
            created_by="system",
            updated_by="system",
        )
        memory_db.add(log_row)
        memory_db.flush()
        memory_db.add(
            EngineeringChangeOrder(
                upload_log_id=log_row.id,
                upload_file_id=upload_file_id,
                before_assembly_node_id=node.id,
                excel_row=2,
                project_code=VEHICLE_MODEL,
                effective_period_text="2025年07月",
                change_type="完成停止",
                before_assembly_part_number=node.part_number,
                part_level="总成",
                status="active",
                created_by="system",
                updated_by="system",
            )
        )
        memory_db.commit()

        with pytest.raises(BusinessException) as caught:
            BomSnapshotService().delete_snapshot(memory_db, snapshot.id)
        assert "仍被引用，不能删除" in caught.value.message
        assert "总成核价" not in caught.value.message
        assert "工程变更" not in caught.value.message

    def test_delete_node_does_not_read_procurement_list(self, memory_db: Session) -> None:
        snapshot = _add_snapshot(memory_db)
        node = _add_node(memory_db, snapshot)
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
        node_id = node.id
        head_id = head.id

        BomNodeService().delete_node(memory_db, node_id)
        assert memory_db.get(BomNode, node_id) is None
        assert memory_db.get(BomProcurementObjectList, head_id) is not None

    def test_orphan_source_node_id_rejected(self, memory_db: Session) -> None:
        with pytest.raises(IntegrityError):
            memory_db.add(
                AssemblyCost(
                    year=2026,
                    month=1,
                    location=LOCATION,
                    vehicle_model=VEHICLE_MODEL,
                    bom_version=BOM_VERSION,
                    source_node_id=1,
                    part_number="ghost",
                    created_by="system",
                    updated_by="system",
                )
            )
            memory_db.commit()
        memory_db.rollback()

    def test_delete_parent_blocked_by_child_cost(self, memory_db: Session) -> None:
        snapshot = _add_snapshot(memory_db)
        parent = _add_node(memory_db, snapshot)
        child = BomNode(
            snapshot_id=snapshot.id,
            parent_id=parent.id,
            level=1,
            part_number="CHILD-1",
            node_role="make",
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version=BOM_VERSION,
            effective_year=2020,
            effective_month=1,
            created_by="system",
            updated_by="system",
        )
        memory_db.add(child)
        memory_db.flush()
        memory_db.add(
            AssemblyCost(
                year=2025,
                month=3,
                location=LOCATION,
                vehicle_model=VEHICLE_MODEL,
                bom_version=BOM_VERSION,
                source_node_id=child.id,
                part_number=child.part_number,
                created_by="system",
                updated_by="system",
            )
        )
        memory_db.commit()

        with pytest.raises(BusinessException) as caught:
            BomNodeService().delete_node(memory_db, parent.id)
        assert "仍被引用，不能删除" in caught.value.message
        assert "总成核价" not in caught.value.message
        assert "2025年03月" not in caught.value.message
        assert memory_db.get(BomNode, parent.id) is not None
