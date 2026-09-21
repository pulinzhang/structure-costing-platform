"""总成核价计算锁：processing unique index 与 409。"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.common.timezone import now
from app.models.costing.assembly_cost_calc_log import AssemblyCostCalcLog
from app.repositories.costing.assembly_cost.assembly_cost_calc_log_repository import (
    AssemblyCostCalcLogRepository,
)
from app.schemas.dto.assembly_cost_dto import AssemblyCostCalcDTO
from app.services.costing.assembly_cost.calc.calc_log import (
    STATUS_FAILED,
    STATUS_PARTIAL,
    STATUS_PROCESSING,
    AssemblyCostCalcLogService,
    DuplicateScopeCalcError,
)

_DTO = AssemblyCostCalcDTO(
    year=2026,
    month=8,
    location="青岛",
    vehicle_model="T28",
)


def _open_session(db_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{db_path}")
    AssemblyCostCalcLog.__table__.create(engine)
    return sessionmaker(bind=engine)()


def _seed_processing(db: Session, *, calc_batch_id: str) -> AssemblyCostCalcLog:
    row = AssemblyCostCalcLog(
        year=_DTO.year,
        month=_DTO.month,
        location=_DTO.location,
        vehicle_model=_DTO.vehicle_model,
        bom_version="",
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
    AssemblyCostCalcLogRepository._lock_index_ensured = False
    db = _open_session(tmp_path / "assembly_calc_log_lock.db")
    try:
        yield db
    finally:
        bind = db.get_bind()
        db.close()
        bind.dispose()
        AssemblyCostCalcLogRepository._lock_index_ensured = False


def test_second_begin_processing_same_scope_is_409(lock_db: Session) -> None:
    service = AssemblyCostCalcLogService()
    first = service.begin_processing(lock_db, _DTO, operator_id=1, operator_name="tester")
    assert first.status == STATUS_PROCESSING

    with pytest.raises(DuplicateScopeCalcError) as caught:
        service.begin_processing(lock_db, _DTO, operator_id=1, operator_name="tester")
    assert caught.value.code == 409

    indexes = inspect(lock_db.get_bind()).get_indexes("costing_assembly_cost_calc_logs")
    names = {item["name"] for item in indexes}
    assert "uq_assembly_calc_processing" in names


def test_begin_processing_ignores_bom_version_for_lock(lock_db: Session) -> None:
    service = AssemblyCostCalcLogService()
    service.begin_processing(lock_db, _DTO, operator_id=1, operator_name="tester")
    other = _DTO.model_copy(update={"bom_version": "D/09"})
    with pytest.raises(DuplicateScopeCalcError):
        service.begin_processing(lock_db, other, operator_id=1, operator_name="tester")


def test_duplicate_processing_rows_are_collapsed_before_index(lock_db: Session) -> None:
    older = _seed_processing(lock_db, calc_batch_id="old-batch")
    newer = _seed_processing(lock_db, calc_batch_id="new-batch")
    service = AssemblyCostCalcLogService()

    with pytest.raises(DuplicateScopeCalcError):
        service.begin_processing(lock_db, _DTO, operator_id=1, operator_name="tester")

    lock_db.expire_all()
    assert lock_db.get(AssemblyCostCalcLog, older.id).status == STATUS_FAILED
    assert lock_db.get(AssemblyCostCalcLog, newer.id).status == STATUS_PROCESSING

    exists = lock_db.execute(
        text(
            "SELECT 1 FROM sqlite_master WHERE type='index' "
            "AND name='uq_assembly_calc_processing'"
        )
    ).scalar()
    assert exists == 1


def test_persist_writes_completed_history_without_processing_lock(lock_db: Session) -> None:
    service = AssemblyCostCalcLogService()
    log_id = service.persist(
        lock_db,
        year=_DTO.year,
        month=_DTO.month,
        location=_DTO.location,
        vehicle_model=_DTO.vehicle_model,
        status=STATUS_PARTIAL,
        message="成功 1，部分成功 2，失败 0，跳过 0",
        subject_total=3,
        ok_count=1,
        partial_count=2,
        failed_count=0,
        skipped_approved_count=0,
        detail_text="卡 A 部分成功：缺冲压件价",
        detail_json='{"cards":[]}',
        operator_id=1,
        operator_name="tester",
    )
    assert log_id is not None
    row = lock_db.get(AssemblyCostCalcLog, log_id)
    assert row is not None
    assert row.status == STATUS_PARTIAL
    assert row.partial_count == 2
    assert row.detail_text.startswith("卡 A")
    assert row.finished_at is not None
