"""成品核价计算锁：processing unique index 与 409。"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.common.timezone import now
from app.models.costing.l0_assembly_cost_calc_log import L0AssemblyCostCalcLog
from app.repositories.costing.l0_assembly_cost.l0_assembly_cost_calc_log_repository import (
    L0AssemblyCostCalcLogRepository,
)
from app.schemas.dto.l0_assembly_cost_dto import L0AssemblyCostCalcDTO
from app.services.costing.l0_assembly_cost.calc.calc_log_service import (
    DuplicateScopeCalcError,
    L0AssemblyCostCalcLogService,
    STATUS_FAILED,
    STATUS_PROCESSING,
)


_DTO = L0AssemblyCostCalcDTO(
    year=2026,
    month=8,
    location="青岛",
    vehicle_model="T28",
    bom_version="V1",
)


def _open_session(db_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{db_path}")
    L0AssemblyCostCalcLog.__table__.create(engine)
    return sessionmaker(bind=engine)()


def _seed_processing(db: Session, *, calc_batch_id: str) -> L0AssemblyCostCalcLog:
    row = L0AssemblyCostCalcLog(
        year=_DTO.year,
        month=_DTO.month,
        location=_DTO.location,
        vehicle_model=_DTO.vehicle_model,
        bom_version=_DTO.bom_version,
        calc_batch_id=calc_batch_id,
        status=STATUS_PROCESSING,
        message="计算中…",
        started_at=now(),
        created_by="test",
        updated_by="test",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@pytest.fixture
def lock_db(tmp_path: Path) -> Generator[Session, None, None]:
    L0AssemblyCostCalcLogRepository._lock_index_ensured = False
    db = _open_session(tmp_path / "l0_calc_log_lock.db")
    try:
        yield db
    finally:
        bind = db.get_bind()
        db.close()
        bind.dispose()
        L0AssemblyCostCalcLogRepository._lock_index_ensured = False


def test_second_begin_processing_same_scope_is_409(lock_db: Session) -> None:
    service = L0AssemblyCostCalcLogService()
    first = service.begin_processing(lock_db, _DTO, operator_id=1, operator_name="tester")
    assert first.status == STATUS_PROCESSING

    with pytest.raises(DuplicateScopeCalcError) as caught:
        service.begin_processing(lock_db, _DTO, operator_id=1, operator_name="tester")
    assert caught.value.code == 409

    indexes = inspect(lock_db.get_bind()).get_indexes("costing_l0_assembly_cost_calc_logs")
    names = {item["name"] for item in indexes}
    assert "uq_l0_assembly_calc_processing" in names


def test_duplicate_processing_rows_are_collapsed_before_index(lock_db: Session) -> None:
    older = _seed_processing(lock_db, calc_batch_id="old-batch")
    newer = _seed_processing(lock_db, calc_batch_id="new-batch")
    service = L0AssemblyCostCalcLogService()

    with pytest.raises(DuplicateScopeCalcError):
        service.begin_processing(lock_db, _DTO, operator_id=1, operator_name="tester")

    lock_db.expire_all()
    assert lock_db.get(L0AssemblyCostCalcLog, older.id).status == STATUS_FAILED
    assert lock_db.get(L0AssemblyCostCalcLog, newer.id).status == STATUS_PROCESSING

    exists = lock_db.execute(
        text(
            "SELECT 1 FROM sqlite_master WHERE type='index' "
            "AND name='uq_l0_assembly_calc_processing'"
        )
    ).scalar()
    assert exists == 1
