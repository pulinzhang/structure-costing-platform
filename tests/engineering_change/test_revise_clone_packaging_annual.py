"""工程变更种新树：包装运输费 / 年度零件价有则抄；回滚删新行、旧行不动。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.common.engineering_change_gates import (
    EFFECT_ANNUAL_PART_PRICE,
    EFFECT_PACKAGING_FEE,
)
from app.database import Base
from app.models.bom.annual_part_price import BomAnnualPartPrice
from app.models.bom.node import BomNode, BomSnapshot
from app.models.bom.packaging_transport_fee import BomPackagingTransportFee
from app.models.masterdata.location import Location
from app.models.masterdata.vehicle_model import VehicleModel
from app.schemas.vo.user_vo import UserVO
from app.services.bom.annual_part_price.service import BomAnnualPartPriceService
from app.services.bom.packaging_transport_fee.service import BomPackagingTransportFeeService
from app.services.engineering_change.list.rollback_service import (
    EngineeringChangeRollbackService,
)
from app.services.engineering_change.upload.persist.annual_part_price import (
    persist_annual_part_prices,
)
from app.services.engineering_change.upload.persist.packaging_fee import persist_packaging_fees

LOCATION = "芜湖"
VEHICLE = "T13J"
USER = UserVO(id=1, username="tester", real_name="测试员")


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
            BomPackagingTransportFee.__table__,
            BomAnnualPartPrice.__table__,
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


def _add_packaging(
    db: Session,
    *,
    part_number: str,
    year: int,
    unit_packaging_fee: Decimal = Decimal("0.1200"),
) -> BomPackagingTransportFee:
    row = BomPackagingTransportFee(
        location=LOCATION,
        year=year,
        vehicle_model=VEHICLE,
        part_number=part_number,
        part_name="流水槽",
        unit_packaging_fee=unit_packaging_fee,
        unit_transport_fee=Decimal("0.3400"),
        fixture_maint_fee=Decimal("0.0100"),
        other_fee=Decimal("0.0200"),
        packaging_transport_total=Decimal("0.4900"),
        audit_status=AUDIT_APPROVED,
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.flush()
    return row


def _add_annual(
    db: Session,
    *,
    part_number: str,
    year: int,
    unit_price: Decimal = Decimal("12.3400"),
) -> BomAnnualPartPrice:
    row = BomAnnualPartPrice(
        location=LOCATION,
        year=year,
        part_number=part_number,
        part_name="后防撞梁",
        conversion_factor=Decimal("2.000000"),
        unit="pcs",
        unit_price=unit_price,
        purchase_unit_price=Decimal("24.6800"),
        supply_type="一口价",
        audit_status=AUDIT_APPROVED,
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.flush()
    return row


def test_clone_packaging_from_effective_year_and_skip(memory_db: Session) -> None:
    service = BomPackagingTransportFeeService()
    assert (
        service.clone_revise_for_engineering_change(
            memory_db,
            location=LOCATION,
            vehicle_model=VEHICLE,
            old_part_number="501006873AA",
            new_part_number="501006873AB",
            from_year=2025,
            current_user=USER,
        )
        == []
    )

    _add_packaging(memory_db, part_number="501006873AA", year=2024)
    old = _add_packaging(memory_db, part_number="501006873AA", year=2025)
    results = service.clone_revise_for_engineering_change(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE,
        old_part_number="501006873AA",
        new_part_number="501006873AB",
        from_year=2025,
        current_user=USER,
    )
    assert len(results) == 1
    assert results[0].before_id == old.id
    new_row = memory_db.query(BomPackagingTransportFee).filter_by(part_number="501006873AB").one()
    assert new_row.year == 2025
    assert new_row.unit_packaging_fee == Decimal("0.1200")
    assert new_row.unit_transport_fee == Decimal("0.3400")
    assert new_row.audit_status == AUDIT_PENDING
    assert (
        memory_db.query(BomPackagingTransportFee)
        .filter_by(part_number="501006873AA", year=2024)
        .count()
        == 1
    )
    assert (
        service.clone_revise_for_engineering_change(
            memory_db,
            location=LOCATION,
            vehicle_model=VEHICLE,
            old_part_number="501006873AA",
            new_part_number="501006873AB",
            from_year=2025,
            current_user=USER,
        )
        == []
    )


def test_clone_annual_copies_unit_price_without_reconversion(memory_db: Session) -> None:
    service = BomAnnualPartPriceService()
    _add_annual(memory_db, part_number="501009122AA-1", year=2024)
    old = _add_annual(memory_db, part_number="501009122AA-1", year=2025)
    results = service.clone_revise_for_engineering_change(
        memory_db,
        location=LOCATION,
        old_part_number="501009122AA-1",
        new_part_number="501009122AB-1",
        from_year=2025,
        current_user=USER,
    )
    assert len(results) == 1
    assert results[0].before_id == old.id
    new_row = memory_db.query(BomAnnualPartPrice).filter_by(part_number="501009122AB-1").one()
    assert new_row.year == 2025
    assert new_row.unit_price == Decimal("12.3400")
    assert new_row.conversion_factor == Decimal("2.000000")
    assert new_row.audit_status == AUDIT_PENDING
    assert (
        memory_db.query(BomAnnualPartPrice)
        .filter_by(part_number="501009122AA-1", year=2024)
        .count()
        == 1
    )


def test_persist_and_rollback_deletes_new_price_rows(memory_db: Session) -> None:
    snapshot = BomSnapshot(
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version="D/00",
        stage="initial",
        status="active",
        source_filename="fixture-bom.xlsx",
        created_by="system",
        updated_by="system",
    )
    memory_db.add(snapshot)
    memory_db.flush()
    old_l0 = BomNode(
        snapshot_id=snapshot.id,
        level=0,
        part_number="501006873AA",
        node_role="supply",
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version="D/00",
        effective_year=2020,
        effective_month=1,
        created_by="system",
        updated_by="system",
    )
    new_l0 = BomNode(
        snapshot_id=snapshot.id,
        level=0,
        part_number="501006873AB",
        node_role="supply",
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version="D/00",
        effective_year=2025,
        effective_month=7,
        created_by="system",
        updated_by="system",
    )
    old_sub = BomNode(
        snapshot_id=snapshot.id,
        level=1,
        part_number="501009122AA-1",
        node_role="structure",
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version="D/00",
        effective_year=2020,
        effective_month=1,
        created_by="system",
        updated_by="system",
    )
    new_sub = BomNode(
        snapshot_id=snapshot.id,
        level=1,
        part_number="501009122AB-1",
        node_role="structure",
        location=LOCATION,
        vehicle_model=VEHICLE,
        bom_version="D/00",
        effective_year=2025,
        effective_month=7,
        created_by="system",
        updated_by="system",
    )
    memory_db.add_all([old_l0, new_l0, old_sub, new_sub])
    memory_db.flush()

    old_pkg = _add_packaging(memory_db, part_number="501006873AA", year=2025)
    old_annual_l0 = _add_annual(memory_db, part_number="501006873AA", year=2025)
    old_annual_sub = _add_annual(memory_db, part_number="501009122AA-1", year=2025)

    pkg_links = persist_packaging_fees(
        memory_db,
        revise_old_to_new={"501006873AA": "501006873AB"},
        part_change_order_index={"501006873AB": 0},
        effective_year=2025,
        location=LOCATION,
        vehicle_model=VEHICLE,
        current_user=USER,
        sort_no_start=20,
    )
    annual_links = persist_annual_part_prices(
        memory_db,
        source_id_remaps=[
            (
                {old_l0.id: new_l0.id, old_sub.id: new_sub.id},
                0,
            )
        ],
        effective_year=2025,
        location=LOCATION,
        current_user=USER,
        sort_no_start=21,
    )
    assert len(pkg_links) == 1
    assert pkg_links[0].effect_kind == EFFECT_PACKAGING_FEE
    assert {link.effect_kind for link in annual_links} == {EFFECT_ANNUAL_PART_PRICE}
    assert len(annual_links) == 2

    new_pkg_id = pkg_links[0].after_id
    assert new_pkg_id is not None
    new_annual_ids = [link.after_id for link in annual_links]
    assert all(item is not None for item in new_annual_ids)

    approved = memory_db.query(BomPackagingTransportFee).filter_by(id=new_pkg_id).one()
    approved.audit_status = AUDIT_APPROVED
    memory_db.flush()

    rollback = EngineeringChangeRollbackService()
    rollback._rollback_link(
        memory_db,
        SimpleNamespace(
            effect_kind=EFFECT_PACKAGING_FEE,
            after_id=new_pkg_id,
            before_id=old_pkg.id,
            id=1,
        ),
        current_user=USER,
    )
    for link in annual_links:
        rollback._rollback_link(
            memory_db,
            SimpleNamespace(
                effect_kind=EFFECT_ANNUAL_PART_PRICE,
                after_id=link.after_id,
                before_id=link.before_id,
                id=2,
            ),
            current_user=USER,
        )
    memory_db.flush()

    assert memory_db.query(BomPackagingTransportFee).filter_by(id=new_pkg_id).count() == 0
    for new_id in new_annual_ids:
        assert memory_db.query(BomAnnualPartPrice).filter_by(id=new_id).count() == 0
    assert memory_db.query(BomPackagingTransportFee).filter_by(id=old_pkg.id).count() == 1
    assert memory_db.query(BomAnnualPartPrice).filter_by(id=old_annual_l0.id).count() == 1
    assert memory_db.query(BomAnnualPartPrice).filter_by(id=old_annual_sub.id).count() == 1
