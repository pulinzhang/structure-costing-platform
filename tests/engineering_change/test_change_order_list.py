"""工程变更单列表实体：变更单一行一条；效果链接挂整本 upload_log_id。"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.engineering_change.change_order import EngineeringChangeOrder
from app.models.engineering_change.effect_link import EngineeringChangeEffectLink
from app.models.engineering_change.upload_log import EngineeringChangeUploadLog
from app.models.file_trace.upload_file import UploadFile
from app.parsers.engineering_change.change_order_parser import CHANGE_ORDER_HEADERS
from app.repositories.engineering_change.change_order_repository import (
    EngineeringChangeOrderInsert,
    EngineeringChangeOrderRepository,
)
from app.repositories.engineering_change.effect_link_repository import (
    EngineeringChangeEffectLinkInsert,
    EngineeringChangeEffectLinkRepository,
)
from app.repositories.engineering_change.upload_log_repository import (
    EngineeringChangeUploadLogInsert,
    EngineeringChangeUploadLogRepository,
)
from app.schemas.dto.engineering_change_dto import EngineeringChangeOrderQueryDTO
from app.services.engineering_change.list.query_service import EngineeringChangeQueryService

CHANGE_ORDER_FIELD_NAMES = (
    "project_code",
    "effective_period_text",
    "change_type",
    "before_assembly_part_number",
    "after_assembly_part_number",
    "assembly_name",
    "part_level",
    "before_part_number",
    "after_part_number",
    "part_name",
)


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
            UploadFile.__table__,
            EngineeringChangeUploadLog.__table__,
            EngineeringChangeOrder.__table__,
            EngineeringChangeEffectLink.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_change_order_columns_match_sample_headers() -> None:
    names = {column.key for column in EngineeringChangeOrder.__table__.columns}
    assert "excel_row" in names
    assert "upload_log_id" in names
    for field_name in CHANGE_ORDER_FIELD_NAMES:
        assert field_name in names
    assert len(CHANGE_ORDER_HEADERS) == 10


def test_effect_link_stores_book_and_entity_ids() -> None:
    names = {column.key for column in EngineeringChangeEffectLink.__table__.columns}
    assert "upload_log_id" in names
    assert "change_order_id" in names
    assert "before_id" in names
    assert "after_id" in names


def _seed_book(db: Session) -> int:
    db.add(
        UploadFile(
            file_category="engineering_change",
            original_filename="t28.xlsx",
            stored_relpath="engineering-change/t28.xlsx",
            file_hash="a" * 64,
            file_size=10,
            extension=".xlsx",
            created_by="tester",
            updated_by="tester",
        )
    )
    db.flush()
    upload_file_id = db.query(UploadFile).one().id
    log_row = EngineeringChangeUploadLogRepository().create(
        db,
        EngineeringChangeUploadLogInsert(
            upload_file_id=upload_file_id,
            location="青岛",
            vehicle_model="T28",
            customer_name="奇瑞",
            effective_year=2025,
            effective_month=7,
            original_filename="t28.xlsx",
            created_by="tester",
            updated_by="tester",
            status="success",
        ),
    )
    change_order_repo = EngineeringChangeOrderRepository()
    first = change_order_repo.create(
        db,
        EngineeringChangeOrderInsert(
            upload_log_id=log_row.id,
            upload_file_id=upload_file_id,
            excel_row=2,
            project_code="T28",
            effective_period_text="2025年07月",
            change_type="完成停止",
            before_assembly_part_number="501006875AA",
            after_assembly_part_number=None,
            assembly_name="总成A",
            part_level="总成",
            before_part_number=None,
            after_part_number=None,
            part_name=None,
            created_by="tester",
            updated_by="tester",
            seq_no=1,
        ),
    )
    second = change_order_repo.create(
        db,
        EngineeringChangeOrderInsert(
            upload_log_id=log_row.id,
            upload_file_id=upload_file_id,
            excel_row=3,
            project_code="T28",
            effective_period_text="2025年07月",
            change_type="改图",
            before_assembly_part_number="501009122AA",
            after_assembly_part_number="501009122AB",
            assembly_name="总成B",
            part_level="一级",
            before_part_number="501007040AA",
            after_part_number="501007040AA",
            part_name="零件",
            created_by="tester",
            updated_by="tester",
            seq_no=2,
        ),
    )
    EngineeringChangeEffectLinkRepository().bulk_create(
        db,
        [
            EngineeringChangeEffectLinkInsert(
                upload_log_id=log_row.id,
                change_order_id=first.id,
                effect_kind="assembly_l0",
                before_id=10,
                after_id=None,
                sort_no=1,
            ),
            EngineeringChangeEffectLinkInsert(
                upload_log_id=log_row.id,
                change_order_id=second.id,
                effect_kind="assembly_l0",
                before_id=11,
                after_id=12,
                sort_no=2,
            ),
        ],
    )
    db.commit()
    return log_row.id


def test_list_is_one_row_per_change_order_same_upload_log_id(memory_db: Session) -> None:
    log_id = _seed_book(memory_db)
    items, total = EngineeringChangeQueryService().paginate(
        memory_db, EngineeringChangeOrderQueryDTO(page=1, size=20)
    )
    assert total == 2
    assert len(items) == 2
    assert {row.upload_log_id for row in items} == {log_id}
    assert {row.change_order_id for row in items} == {1, 2}
    assert [row.excel_row for row in items] == [2, 3]
    assert items[0].change_type == "完成停止"
    assert items[1].change_type == "改图"


def test_delete_rolls_back_and_physically_deletes_whole_book(memory_db: Session) -> None:
    from unittest.mock import MagicMock

    from app.schemas.vo.user_vo import UserVO
    from app.services.engineering_change.list.rollback_service import (
        EngineeringChangeRollbackService,
    )

    log_id = _seed_book(memory_db)
    service = EngineeringChangeRollbackService()
    service.bom_service = MagicMock()
    service.po_service = MagicMock()
    service.breakdown_service = MagicMock()
    service.stamping_service = MagicMock()
    service.die_service = MagicMock()
    service.rollback(memory_db, log_id, UserVO(id=1, username="tester", real_name="测试员"))
    assert memory_db.query(EngineeringChangeUploadLog).count() == 0
    assert memory_db.query(EngineeringChangeOrder).count() == 0
    assert memory_db.query(EngineeringChangeEffectLink).count() == 0
    assert memory_db.query(UploadFile).count() == 1
    assert service.bom_service.delete_engineering_change_tree.called
    assert service.bom_service.clear_l0_expiry.called


def test_effect_links_belong_to_whole_book(memory_db: Session) -> None:
    log_id = _seed_book(memory_db)
    links = EngineeringChangeEffectLinkRepository().list_by_upload_log_id_desc(memory_db, log_id)
    assert len(links) == 2
    assert {link.upload_log_id for link in links} == {log_id}
    assert [link.sort_no for link in links] == [2, 1]
