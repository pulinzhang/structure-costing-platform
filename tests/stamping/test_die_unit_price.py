"""冲压模具单价档案：工艺范围校验、唯一键、规范化项目、状态更新。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.exceptions.base import BusinessException, NotFoundException
from app.models.stamping.die_unit_price import (
    STATUS_EFFECTIVE,
    STATUS_INVALID,
    StampingDieUnitPrice,
)
from app.models.stamping.part import StampingPart
from app.schemas.dto.stamping_die_unit_price_dto import (
    StampingDieUnitPriceCreate,
    StampingDieUnitPriceQuery,
    StampingDieUnitPriceUpdate,
)
from app.services.stamping.die.unit_price_service import StampingDieUnitPriceService


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[StampingPart.__table__, StampingDieUnitPrice.__table__],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _add_process_part(
    db: Session,
    *,
    location: str = "芜湖",
    vehicle_model: str = "T13J",
    part_number: str = "501006875AA",
) -> None:
    db.add(
        StampingPart(
            location=location,
            vehicle_model=vehicle_model,
            version="V1",
            part_number=part_number,
            excel_filename="T13J工艺确认表.xlsx",
        )
    )
    db.commit()


def _create_dto(**overrides: object) -> StampingDieUnitPriceCreate:
    payload = {
        "location": "芜湖",
        "vehicle_model": "T13J",
        "steel_plate_unit_price": Decimal("3.36"),
        "progressive_die_unit_price": Decimal("5.15"),
        "allocation_qty": Decimal("10"),
        "status": STATUS_EFFECTIVE,
    }
    payload.update(overrides)
    return StampingDieUnitPriceCreate(**payload)


def test_create_rejects_missing_process_scope(memory_db: Session) -> None:
    service = StampingDieUnitPriceService()
    with pytest.raises(BusinessException, match="冲压工艺库中不存在"):
        service.create(memory_db, _create_dto(), current_user=SYSTEM_USER)


def test_create_normalizes_vehicle_and_lists(memory_db: Session) -> None:
    _add_process_part(memory_db)
    service = StampingDieUnitPriceService()
    created = service.create(
        memory_db,
        _create_dto(vehicle_model="芜湖T13J"),
        current_user=SYSTEM_USER,
    )
    assert created.vehicle_model == "T13J"
    assert created.location == "芜湖"
    assert created.steel_plate_unit_price == Decimal("3.3600")
    assert created.allocation_qty == Decimal("10.0000")
    assert created.status == STATUS_EFFECTIVE
    assert created.status_label == "生效"

    items, total = service.paginate(
        memory_db,
        StampingDieUnitPriceQuery(location="芜湖", vehicle_model="T13J", page=1, size=10),
    )
    assert total == 1
    assert items[0].id == created.id


def test_duplicate_scope_is_conflict(memory_db: Session) -> None:
    _add_process_part(memory_db)
    service = StampingDieUnitPriceService()
    service.create(memory_db, _create_dto(), current_user=SYSTEM_USER)
    with pytest.raises(BusinessException) as exc_info:
        service.create(memory_db, _create_dto(), current_user=SYSTEM_USER)
    assert exc_info.value.code == 409
    assert "芜湖" in exc_info.value.message
    assert "T13J" in exc_info.value.message
    assert "UNIQUE" not in exc_info.value.message.upper()
    assert "constraint" not in exc_info.value.message.lower()


def test_update_to_existing_scope_is_rejected(memory_db: Session) -> None:
    _add_process_part(memory_db)
    _add_process_part(memory_db, vehicle_model="T28", part_number="501006876AA")
    service = StampingDieUnitPriceService()
    t13j = service.create(memory_db, _create_dto(), current_user=SYSTEM_USER)
    t28 = service.create(
        memory_db,
        _create_dto(vehicle_model="T28"),
        current_user=SYSTEM_USER,
    )
    with pytest.raises(BusinessException) as exc_info:
        service.update(
            memory_db,
            t28.id,
            StampingDieUnitPriceUpdate(location="芜湖", vehicle_model="T13J"),
            current_user=SYSTEM_USER,
        )
    assert exc_info.value.code == 409
    assert "T13J" in exc_info.value.message
    still_t28 = service.get_by_id(memory_db, t28.id)
    assert still_t28.vehicle_model == "T28"
    same_t13j = service.update(
        memory_db,
        t13j.id,
        StampingDieUnitPriceUpdate(location="芜湖", vehicle_model="T13J", status=STATUS_INVALID),
        current_user=SYSTEM_USER,
    )
    assert same_t13j.status == STATUS_INVALID


def test_update_status_and_reject_missing(memory_db: Session) -> None:
    _add_process_part(memory_db)
    service = StampingDieUnitPriceService()
    created = service.create(memory_db, _create_dto(), current_user=SYSTEM_USER)
    updated = service.update(
        memory_db,
        created.id,
        StampingDieUnitPriceUpdate(status=STATUS_INVALID),
        current_user=SYSTEM_USER,
    )
    assert updated.status == STATUS_INVALID
    assert updated.status_label == "失效"
    assert updated.steel_plate_unit_price == Decimal("3.3600")

    with pytest.raises(NotFoundException):
        service.get_by_id(memory_db, 99999)


def test_delete(memory_db: Session) -> None:
    _add_process_part(memory_db)
    service = StampingDieUnitPriceService()
    created = service.create(memory_db, _create_dto(), current_user=SYSTEM_USER)
    service.delete(memory_db, created.id)
    with pytest.raises(NotFoundException):
        service.get_by_id(memory_db, created.id)


def test_wuhu_t13j_full_lifecycle(memory_db: Session) -> None:
    """芜湖 + T13J：筛选项 → 新增示例价 → 列表/详情 → 失效 → 改回 → 冲突 → 删除。"""
    _add_process_part(memory_db)
    service = StampingDieUnitPriceService()

    filters = service.list_scope_filters(memory_db, "芜湖")
    assert "芜湖" in filters.locations
    assert "T13J" in filters.vehicle_models

    created = service.create(memory_db, _create_dto(), current_user=SYSTEM_USER)
    assert created.location == "芜湖"
    assert created.vehicle_model == "T13J"
    assert created.steel_plate_unit_price == Decimal("3.3600")
    assert created.progressive_die_unit_price == Decimal("5.1500")
    assert created.allocation_qty == Decimal("10.0000")
    assert created.status == STATUS_EFFECTIVE

    detail = service.get_by_id(memory_db, created.id)
    assert detail.id == created.id

    effective_rows, effective_total = service.paginate(
        memory_db,
        StampingDieUnitPriceQuery(
            location="芜湖",
            vehicle_model="T13J",
            status=STATUS_EFFECTIVE,
            page=1,
            size=10,
        ),
    )
    assert effective_total == 1
    assert effective_rows[0].id == created.id

    invalidated = service.update(
        memory_db,
        created.id,
        StampingDieUnitPriceUpdate(status=STATUS_INVALID),
        current_user=SYSTEM_USER,
    )
    assert invalidated.status == STATUS_INVALID
    empty_effective, empty_total = service.paginate(
        memory_db,
        StampingDieUnitPriceQuery(
            location="芜湖",
            vehicle_model="T13J",
            status=STATUS_EFFECTIVE,
            page=1,
            size=10,
        ),
    )
    assert empty_total == 0
    assert empty_effective == []

    restored = service.update(
        memory_db,
        created.id,
        StampingDieUnitPriceUpdate(
            steel_plate_unit_price=Decimal("3.36"),
            progressive_die_unit_price=Decimal("5.15"),
            allocation_qty=Decimal("10"),
            status=STATUS_EFFECTIVE,
        ),
        current_user=SYSTEM_USER,
    )
    assert restored.status == STATUS_EFFECTIVE
    assert restored.allocation_qty == Decimal("10.0000")

    with pytest.raises(BusinessException) as exc_info:
        service.create(memory_db, _create_dto(), current_user=SYSTEM_USER)
    assert exc_info.value.code == 409

    service.delete(memory_db, created.id)
    with pytest.raises(NotFoundException):
        service.get_by_id(memory_db, created.id)
