"""工程变更改图：检具费 / 模具费有则抄；回滚删新行、旧行不动。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.common.engineering_change_gates import EFFECT_DIE_FEE, EFFECT_GAUGE_FEE
from app.database import Base
from app.models.masterdata.location import Location
from app.models.masterdata.vehicle_model import VehicleModel
from app.models.stamping.die import StampingDiePart, StampingDieProcess
from app.models.stamping.die_fee import StampingDieFee
from app.models.stamping.die_fee_item import StampingDieFeeItem
from app.models.stamping.gauge_fee import STATUS_EFFECTIVE, StampingGaugeFee
from app.repositories.stamping.die_fee.repository import StampingDieFeeRepository
from app.schemas.dto.stamping_die_fee_dto import DieFeeInsertPayload, DieFeeItemPayload
from app.schemas.vo.user_vo import UserVO
from app.services.engineering_change.list.rollback_service import (
    EngineeringChangeRollbackService,
)
from app.services.engineering_change.upload.persist.die_fee import persist_die_fees
from app.services.engineering_change.upload.persist.gauge_fee import persist_gauge_fees
from app.services.stamping.die_fee.crud.service import StampingDieFeeService
from app.services.stamping.gauge_fee.crud.service import StampingGaugeFeeService

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
            StampingDiePart.__table__,
            StampingDieProcess.__table__,
            StampingGaugeFee.__table__,
            StampingDieFee.__table__,
            StampingDieFeeItem.__table__,
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


def _add_die_part(db: Session, *, part_number: str, version: str | None = "V1") -> StampingDiePart:
    row = StampingDiePart(
        location=LOCATION,
        vehicle_model=VEHICLE,
        version=version,
        seq_no=1,
        part_number=part_number,
        part_name="左后尾灯安装板",
        stamping_supplier="安徽振华",
        material="DC56D+Z",
        thickness=Decimal("0.65"),
        part_weight=Decimal("0.383"),
        effective_year=2025,
        effective_month=1,
        excel_filename="模具布点.xlsx",
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.flush()
    return row


def _add_gauge(db: Session, *, part_number: str) -> StampingGaugeFee:
    row = StampingGaugeFee(
        location=LOCATION,
        vehicle_model=VEHICLE,
        part_number=part_number,
        part_name="左后尾灯安装板",
        gauge_fee=Decimal("0.8000"),
        allocation_qty=Decimal("10"),
        status=STATUS_EFFECTIVE,
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.flush()
    return row


def _add_die_fee(db: Session, *, part_number: str, year: int, die_part_id: int) -> StampingDieFee:
    return StampingDieFeeRepository().insert_with_items(
        db,
        DieFeeInsertPayload(
            year=year,
            location=LOCATION,
            vehicle_model=VEHICLE,
            stamping_supplier="安徽振华",
            version="V1",
            part_number=part_number,
            source_die_part_id=die_part_id,
            seq_no=1,
            part_name="左后尾灯安装板",
            material="DC56D+Z",
            thickness=Decimal("0.65"),
            part_weight=Decimal("0.383"),
            die_type="铸造模",
            die_method="双槽",
            production_mode="手工线",
            part_grade="B+",
            excel_filename=None,
            price_kind="steel_plate",
            unit_price=Decimal("3.3600"),
            allocation_qty=Decimal("10"),
            die_fee=Decimal("1.2000"),
            adjustment_amount=Decimal("0.1000"),
            final_die_fee=Decimal("1.3000"),
            audit_status=AUDIT_APPROVED,
            created_by="system",
            updated_by="system",
            items=[
                DieFeeItemPayload(
                    source_die_process_id=99,
                    process_seq="OP10",
                    process_order=1,
                    process_code="DR",
                    estimated_weight_t=Decimal("0.5000"),
                    alloc_ratio=Decimal("0.50"),
                    die_sets=1,
                    unit_price=Decimal("3.3600"),
                    allocation_qty=Decimal("10"),
                    price_kind="steel_plate",
                    line_die_fee=Decimal("1.2000"),
                    basis_text="自有重量",
                )
            ],
        ),
    )


def test_clone_gauge_fee_and_skip_when_missing_or_exists(memory_db: Session) -> None:
    service = StampingGaugeFeeService()
    assert (
        service.clone_revise_for_engineering_change(
            memory_db,
            location=LOCATION,
            vehicle_model=VEHICLE,
            old_part_number="502007710AA",
            new_part_number="502007710AB",
            current_user=USER,
        )
        is None
    )

    old = _add_gauge(memory_db, part_number="502007710AA")
    result = service.clone_revise_for_engineering_change(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE,
        old_part_number="502007710AA",
        new_part_number="502007710AB",
        current_user=USER,
    )
    assert result is not None
    assert result.before_id == old.id
    new_row = memory_db.query(StampingGaugeFee).filter_by(part_number="502007710AB").one()
    assert new_row.id == result.after_id
    assert new_row.gauge_fee == Decimal("0.8000")
    assert new_row.allocation_qty == Decimal("10")
    assert memory_db.query(StampingGaugeFee).filter_by(part_number="502007710AA").count() == 1

    assert (
        service.clone_revise_for_engineering_change(
            memory_db,
            location=LOCATION,
            vehicle_model=VEHICLE,
            old_part_number="502007710AA",
            new_part_number="502007710AB",
            current_user=USER,
        )
        is None
    )


def test_clone_die_fee_from_effective_year(memory_db: Session) -> None:
    old_die = _add_die_part(memory_db, part_number="502007710AA")
    new_die = _add_die_part(memory_db, part_number="502007710AB", version="EC-202505")
    _add_die_fee(memory_db, part_number="502007710AA", year=2024, die_part_id=old_die.id)
    old_fee = _add_die_fee(memory_db, part_number="502007710AA", year=2025, die_part_id=old_die.id)

    results = StampingDieFeeService().clone_revise_for_engineering_change(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE,
        old_part_number="502007710AA",
        new_part_number="502007710AB",
        from_year=2025,
        new_die_part_id=new_die.id,
        current_user=USER,
    )
    assert len(results) == 1
    assert results[0].before_id == old_fee.id
    new_fee = memory_db.query(StampingDieFee).filter_by(part_number="502007710AB").one()
    assert new_fee.year == 2025
    assert new_fee.final_die_fee == Decimal("1.3000")
    assert new_fee.adjustment_amount == Decimal("0.1000")
    assert new_fee.source_die_part_id == new_die.id
    assert new_fee.version == "EC-202505"
    assert new_fee.audit_status == AUDIT_PENDING
    assert len(new_fee.items) == 1
    assert new_fee.items[0].source_die_process_id is None
    assert (
        memory_db.query(StampingDieFee).filter_by(part_number="502007710AA", year=2024).count() == 1
    )
    assert (
        memory_db.query(StampingDieFee).filter_by(part_number="502007710AA", year=2025).count() == 1
    )


def test_persist_and_rollback_deletes_new_fee_rows(memory_db: Session) -> None:
    old_die = _add_die_part(memory_db, part_number="502007710AA")
    new_die = _add_die_part(memory_db, part_number="502007710AB", version="EC-202505")
    old_gauge = _add_gauge(memory_db, part_number="502007710AA")
    old_fee = _add_die_fee(memory_db, part_number="502007710AA", year=2025, die_part_id=old_die.id)

    revise = {"502007710AA": "502007710AB"}
    index = {"502007710AB": 0}
    gauge_links = persist_gauge_fees(
        memory_db,
        revise_old_to_new=revise,
        part_change_order_index=index,
        location=LOCATION,
        vehicle_model=VEHICLE,
        current_user=USER,
        sort_no_start=10,
    )
    die_fee_links = persist_die_fees(
        memory_db,
        revise_old_to_new=revise,
        part_change_order_index=index,
        new_die_part_ids={"502007710AB": new_die.id},
        effective_year=2025,
        location=LOCATION,
        vehicle_model=VEHICLE,
        current_user=USER,
        sort_no_start=11,
    )
    assert len(gauge_links) == 1
    assert len(die_fee_links) == 1
    assert gauge_links[0].effect_kind == EFFECT_GAUGE_FEE
    assert die_fee_links[0].effect_kind == EFFECT_DIE_FEE
    assert gauge_links[0].sort_no == 10
    assert die_fee_links[0].sort_no == 11

    new_gauge_id = gauge_links[0].after_id
    new_fee_id = die_fee_links[0].after_id
    assert new_gauge_id is not None
    assert new_fee_id is not None

    rollback = EngineeringChangeRollbackService()
    rollback._rollback_link(
        memory_db,
        SimpleNamespace(
            effect_kind=EFFECT_DIE_FEE, after_id=new_fee_id, before_id=old_fee.id, id=1
        ),
        current_user=USER,
    )
    rollback._rollback_link(
        memory_db,
        SimpleNamespace(
            effect_kind=EFFECT_GAUGE_FEE, after_id=new_gauge_id, before_id=old_gauge.id, id=2
        ),
        current_user=USER,
    )
    memory_db.flush()

    assert memory_db.query(StampingGaugeFee).filter_by(id=new_gauge_id).count() == 0
    assert memory_db.query(StampingDieFee).filter_by(id=new_fee_id).count() == 0
    assert memory_db.query(StampingDieFeeItem).filter_by(fee_id=new_fee_id).count() == 0
    assert memory_db.query(StampingGaugeFee).filter_by(id=old_gauge.id).count() == 1
    assert memory_db.query(StampingDieFee).filter_by(id=old_fee.id).count() == 1
