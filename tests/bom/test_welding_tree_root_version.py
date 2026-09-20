"""拆解/焊接费：列表删筛认树根；存量行头字不是范围真相。"""

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
    BomWeldingFee,
    BomWeldingFeeItem,
    BomWeldingProcessBreakdownLine,
    BomWeldingProcessBreakdownNode,
)
from app.models.masterdata.location import Location
from app.models.masterdata.vehicle_model import VehicleModel
from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.services.bom.bom.period import BomPeriodService
from app.services.bom.welding_process_breakdown.query import overlay_breakdown_vos

LOCATION = "青岛"
VEHICLE_MODEL = "T28"
SOP_VERSION = "D/09"
EC_VERSION = "EC-202505"


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
        bom_version=SOP_VERSION,
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


def _l0(
    db: Session,
    snapshot: BomSnapshot,
    *,
    part_number: str,
    tree_version: str,
    excel_row: int,
) -> BomNode:
    row = BomNode(
        snapshot_id=snapshot.id,
        parent_id=None,
        level=0,
        seq_no=10,
        excel_row=excel_row,
        part_number=part_number,
        part_name=part_number,
        node_role="supply",
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=tree_version,
        effective_year=2020,
        effective_month=1,
        expiry_year=None,
        expiry_month=None,
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
    stored_version: str,
) -> BomWeldingProcessBreakdownNode:
    row = BomWeldingProcessBreakdownNode(
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=stored_version,
        snapshot_id=source.snapshot_id,
        source_node_id=source.id,
        part_number=source.part_number,
        part_name=source.part_name,
        level=0,
        node_role="supply",
        supply_part_number=source.part_number,
        supply_part_name=source.part_name,
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


def _fee(db: Session, breakdown: BomWeldingProcessBreakdownNode) -> BomWeldingFee:
    row = BomWeldingFee(
        year=2026,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=breakdown.bom_version,
        level=0,
        source_breakdown_node_id=breakdown.id,
        part_number=breakdown.part_number,
        process_line_count=1,
        matched_line_count=1,
        missing_price_count=0,
        total_welding_fee=Decimal("1"),
        final_welding_fee=Decimal("1"),
        calc_status="success",
        audit_status="pending",
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _two_trees(
    db: Session,
) -> tuple[BomWeldingProcessBreakdownNode, BomWeldingProcessBreakdownNode]:
    snapshot = _snapshot(db)
    sop = _l0(db, snapshot, part_number="ROOT-AA", tree_version=SOP_VERSION, excel_row=2)
    ec = _l0(db, snapshot, part_number="ROOT-AB", tree_version=EC_VERSION, excel_row=2)
    sop_bd = _breakdown(db, source=sop, stored_version=SOP_VERSION)
    ec_bd = _breakdown(db, source=ec, stored_version=SOP_VERSION)
    return sop_bd, ec_bd


def test_distinct_versions_are_tree_roots_not_stored_header(memory_db: Session) -> None:
    _two_trees(memory_db)
    versions = BomPeriodService().list_l0_versions(
        memory_db, location=LOCATION, vehicle_model=VEHICLE_MODEL
    )
    assert versions == [SOP_VERSION, EC_VERSION]


def _source_ids(db: Session, bom_version: str) -> set[int]:
    ids = BomPeriodService().node_ids_for_l0_version(
        db,
        bom_version=bom_version,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
    )
    return ids or set()


def test_list_by_ec_version_does_not_include_sop_tree(memory_db: Session) -> None:
    sop_bd, ec_bd = _two_trees(memory_db)
    repo = BomWeldingProcessBreakdownRepository()
    rows = repo.list_by_scope(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        source_node_ids=_source_ids(memory_db, EC_VERSION),
    )
    assert {row.id for row in rows} == {ec_bd.id}
    by_header = repo.list_by_scope(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        source_node_ids=_source_ids(memory_db, SOP_VERSION),
    )
    assert {row.id for row in by_header} == {sop_bd.id}


def test_delete_by_ec_version_leaves_sop_tree(memory_db: Session) -> None:
    sop_bd, ec_bd = _two_trees(memory_db)
    sop_id = int(sop_bd.id)
    ec_id = int(ec_bd.id)
    repo = BomWeldingProcessBreakdownRepository()
    deleted = repo.delete_unaudited_by_scope(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        source_node_ids=_source_ids(memory_db, EC_VERSION),
    )
    memory_db.commit()
    assert deleted == 1
    assert memory_db.query(BomWeldingProcessBreakdownNode).filter_by(id=sop_id).first() is not None
    assert memory_db.query(BomWeldingProcessBreakdownNode).filter_by(id=ec_id).first() is None


def test_generate_delete_by_snapshot_id_clears_pack(memory_db: Session) -> None:
    sop_bd, ec_bd = _two_trees(memory_db)
    snapshot_id = int(sop_bd.snapshot_id or 0)
    sop_id = int(sop_bd.id)
    ec_id = int(ec_bd.id)
    repo = BomWeldingProcessBreakdownRepository()
    deleted = repo.delete_unaudited_by_snapshot_id(memory_db, snapshot_id)
    memory_db.commit()
    assert deleted == 2
    assert memory_db.query(BomWeldingProcessBreakdownNode).filter_by(id=sop_id).first() is None
    assert memory_db.query(BomWeldingProcessBreakdownNode).filter_by(id=ec_id).first() is None


def test_list_order_uses_seq_slot_then_part_number(memory_db: Session) -> None:
    sop_bd, ec_bd = _two_trees(memory_db)
    rows, total = BomWeldingProcessBreakdownRepository().paginate(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        skip=0,
        limit=20,
    )
    assert total == 2
    assert [row.part_number for row in rows] == ["ROOT-AA", "ROOT-AB"]
    assert rows[0].id == sop_bd.id
    assert rows[1].id == ec_bd.id


def test_overlay_vo_shows_tree_root_version(memory_db: Session) -> None:
    _sop_bd, ec_bd = _two_trees(memory_db)
    vos = overlay_breakdown_vos(memory_db, [ec_bd])
    assert vos[0].bom_version == EC_VERSION


def test_fee_list_and_delete_follow_tree_root(memory_db: Session) -> None:
    sop_bd, ec_bd = _two_trees(memory_db)
    sop_fee = _fee(memory_db, sop_bd)
    ec_fee = _fee(memory_db, ec_bd)
    fee_repo = BomWeldingFeeRepository()
    versions = BomPeriodService().list_l0_versions(
        memory_db, year=2026, location=LOCATION, vehicle_model=VEHICLE_MODEL
    )
    assert versions == [SOP_VERSION, EC_VERSION]
    rows, total = fee_repo.paginate(
        memory_db,
        year=2026,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        source_node_ids=_source_ids(memory_db, EC_VERSION),
        skip=0,
        limit=20,
    )
    assert total == 1
    assert rows[0].id == ec_fee.id
    sop_fee_id = int(sop_fee.id)
    ec_fee_id = int(ec_fee.id)
    deleted = fee_repo.delete_unaudited_by_scope(
        memory_db,
        year=2026,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        source_node_ids=_source_ids(memory_db, EC_VERSION),
    )
    memory_db.commit()
    assert deleted == 1
    assert memory_db.query(BomWeldingFee).filter_by(id=sop_fee_id).first() is not None
    assert memory_db.query(BomWeldingFee).filter_by(id=ec_fee_id).first() is None


def test_year_overlap_includes_both_trees(memory_db: Session) -> None:
    sop_bd, ec_bd = _two_trees(memory_db)
    ids = BomPeriodService().node_ids_overlapping_year(
        memory_db, location=LOCATION, vehicle_model=VEHICLE_MODEL, year=2026
    )
    rows = BomWeldingProcessBreakdownRepository().list_by_source_node_ids(memory_db, list(ids))
    assert {row.id for row in rows} == {sop_bd.id, ec_bd.id}
