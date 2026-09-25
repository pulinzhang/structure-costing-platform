"""删除前引用检查：计数、话术、短句与操作日志明细。"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.requests import Request

from app.bootstrap.exception_handlers import register_exception_handlers
from app.exceptions.base import BusinessException
from app.exceptions.handlers import business_exception_handler
from app.middleware.operation_log_middleware import OperationLogMiddleware
from app.models.settings.foreign_key.ref_hint import RefHint
from app.models.settings.foreign_key.schema_comment import SchemaComment
from app.models.settings.operation_log import OperationLog
from app.services.settings.foreign_key.seed import ensure_schema_reference_seed
from app.services.settings.foreign_key.service import STILL_REFERENCED, ensure_deletable
from app.services.settings.logs.service import OperationLogService


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "DELETE",
            "scheme": "http",
            "path": "/api/masterdata/locations/wuhu",
            "raw_path": b"/api/masterdata/locations/wuhu",
            "query_string": b"",
            "headers": [],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }
    )


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    def _enable_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    from sqlalchemy import event

    event.listen(engine, "connect", _enable_foreign_keys)
    SchemaComment.__table__.create(engine)
    RefHint.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    session.execute(text("CREATE TABLE parents (id INTEGER PRIMARY KEY, location TEXT, code TEXT)"))
    session.execute(
        text(
            "CREATE TABLE restrict_kids ("
            "id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL, "
            "FOREIGN KEY(parent_id) REFERENCES parents(id) ON DELETE RESTRICT)"
        )
    )
    session.execute(
        text(
            "CREATE TABLE cascade_kids ("
            "id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL, "
            "FOREIGN KEY(parent_id) REFERENCES parents(id) ON DELETE CASCADE)"
        )
    )
    session.execute(
        text(
            "CREATE TABLE null_kids ("
            "id INTEGER PRIMARY KEY, parent_id INTEGER, "
            "FOREIGN KEY(parent_id) REFERENCES parents(id) ON DELETE SET NULL)"
        )
    )
    session.execute(
        text(
            "CREATE TABLE projects ("
            "location TEXT NOT NULL, vehicle_model TEXT NOT NULL, "
            "PRIMARY KEY (location, vehicle_model))"
        )
    )
    session.execute(
        text(
            "CREATE TABLE snaps ("
            "id INTEGER PRIMARY KEY, location TEXT NOT NULL, vehicle_model TEXT NOT NULL, "
            "FOREIGN KEY(location, vehicle_model) "
            "REFERENCES projects(location, vehicle_model) ON DELETE RESTRICT)"
        )
    )
    session.execute(
        text(
            "CREATE TABLE zeta_kids ("
            "id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL, "
            "FOREIGN KEY(parent_id) REFERENCES parents(id) ON DELETE RESTRICT)"
        )
    )
    session.execute(
        text(
            "CREATE TABLE no_action_kids ("
            "id INTEGER PRIMARY KEY, parent_id INTEGER NOT NULL, "
            "FOREIGN KEY(parent_id) REFERENCES parents(id))"
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_no_reference_allows_delete(memory_db: Session) -> None:
    memory_db.execute(text("INSERT INTO parents (id) VALUES (1)"))
    memory_db.commit()
    ensure_deletable(memory_db, "parents", [{"id": 1}], subject="基地「芜湖」")


def test_restrict_count_uses_hint_and_short_message(memory_db: Session) -> None:
    memory_db.add(
        SchemaComment(
            table_name="restrict_kids", slice="stamping", name_zh="冲压零件", name_en="part"
        )
    )
    memory_db.add(
        RefHint(parent_table="parents", child_table="restrict_kids", hint="请先处理这些冲压零件")
    )
    memory_db.execute(text("INSERT INTO parents (id) VALUES (1)"))
    memory_db.execute(text("INSERT INTO restrict_kids (parent_id) VALUES (1), (1)"))
    memory_db.commit()
    with pytest.raises(BusinessException) as caught:
        ensure_deletable(memory_db, "parents", [{"id": 1}], subject="基地「芜湖」")
    assert caught.value.message == STILL_REFERENCED
    assert caught.value.audit_detail == (
        "无法删除基地「芜湖」，原因如下：\n"
        "  - 有 2 条冲压零件，请先处理这些冲压零件\n"
        "请处理完以上数据后再删除。"
    )


def test_cascade_and_set_null_do_not_count(memory_db: Session) -> None:
    memory_db.execute(text("INSERT INTO parents (id) VALUES (1)"))
    memory_db.execute(text("INSERT INTO cascade_kids (parent_id) VALUES (1)"))
    memory_db.execute(text("INSERT INTO null_kids (parent_id) VALUES (1)"))
    memory_db.commit()
    ensure_deletable(memory_db, "parents", [{"id": 1}])


def test_composite_and_multi_row(memory_db: Session) -> None:
    memory_db.execute(
        text("INSERT INTO projects (location, vehicle_model) VALUES ('芜湖', 'A'), ('青岛', 'B')")
    )
    memory_db.execute(
        text("INSERT INTO snaps (location, vehicle_model) VALUES ('芜湖', 'A'), ('芜湖', 'A')")
    )
    memory_db.commit()
    with pytest.raises(BusinessException) as caught:
        ensure_deletable(
            memory_db,
            "projects",
            [
                {"location": "芜湖", "vehicle_model": "A"},
                {"location": "青岛", "vehicle_model": "B"},
            ],
        )
    assert "被 snaps 表引用 2 条" in (caught.value.audit_detail or "")


def test_bullets_sort_by_child_table(memory_db: Session) -> None:
    memory_db.execute(text("INSERT INTO parents (id) VALUES (1)"))
    memory_db.execute(text("INSERT INTO restrict_kids (parent_id) VALUES (1)"))
    memory_db.execute(text("INSERT INTO zeta_kids (parent_id) VALUES (1)"))
    memory_db.commit()
    with pytest.raises(BusinessException) as caught:
        ensure_deletable(memory_db, "parents", [{"id": 1}])
    detail = caught.value.audit_detail or ""
    assert detail.index("restrict_kids") < detail.index("zeta_kids")


def test_name_without_hint(memory_db: Session) -> None:
    memory_db.add(
        SchemaComment(
            table_name="restrict_kids",
            slice="costing",
            name_zh="冲压零件价格",
            name_en="part cost",
        )
    )
    memory_db.execute(text("INSERT INTO parents (id) VALUES (1)"))
    memory_db.execute(text("INSERT INTO restrict_kids (parent_id) VALUES (1)"))
    memory_db.commit()
    with pytest.raises(BusinessException) as caught:
        ensure_deletable(memory_db, "parents", [{"id": 1}])
    assert "有 1 条冲压零件价格，请先处理冲压零件价格" in (caught.value.audit_detail or "")


def test_missing_parent_warns_and_returns(
    memory_db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        ensure_deletable(memory_db, "missing_parents", [{"id": 1}])
    assert "missing_parents" in caplog.text


def test_no_action_blocks_delete(memory_db: Session) -> None:
    memory_db.execute(text("INSERT INTO parents (id) VALUES (1)"))
    memory_db.execute(text("INSERT INTO no_action_kids (parent_id) VALUES (1)"))
    memory_db.commit()
    with pytest.raises(BusinessException) as caught:
        ensure_deletable(memory_db, "parents", [{"id": 1}])
    assert "no_action_kids" in (caught.value.audit_detail or "")


def test_empty_keys_and_illegal_table_name(memory_db: Session) -> None:
    ensure_deletable(memory_db, "parents", [])
    with pytest.raises(ValueError, match="非法父表名"):
        ensure_deletable(memory_db, "parents;drop", [{"id": 1}])


def test_missing_parent_column_raises(memory_db: Session) -> None:
    memory_db.execute(text("INSERT INTO projects (location, vehicle_model) VALUES ('芜湖', 'A')"))
    memory_db.commit()
    with pytest.raises(ValueError, match="缺少父列"):
        ensure_deletable(memory_db, "projects", [{"location": "芜湖"}])


def test_seed_upsert_keeps_extra_row(memory_db: Session) -> None:
    memory_db.add(
        SchemaComment(table_name="gone_table", slice="settings", name_zh="已下线", name_en="gone")
    )
    memory_db.commit()
    ensure_schema_reference_seed(memory_db)
    kept = memory_db.get(SchemaComment, "gone_table")
    assert kept is not None
    assert kept.name_zh == "已下线"
    comment = memory_db.get(SchemaComment, "locations")
    assert comment is not None
    assert comment.name_zh == "基地"
    hint = memory_db.get(RefHint, ("locations", "vehicle_models"))
    assert hint is not None
    assert hint.hint == "请到「主数据 → 项目 → 一览」处理"
    memory_db.add(
        RefHint(parent_table="locations", child_table="kept_child", hint="请先处理这些保留")
    )
    memory_db.commit()
    ensure_schema_reference_seed(memory_db)
    kept_hint = memory_db.get(RefHint, ("locations", "kept_child"))
    assert kept_hint is not None
    assert kept_hint.hint == "请先处理这些保留"


def test_handler_returns_detail_and_keeps_short_log_message() -> None:
    request = _request()
    detail = "无法删除基地「芜湖」，原因如下：\n  - 有 2 条项目，请先处理这些项目"
    response = asyncio.run(
        business_exception_handler(
            request,
            BusinessException(STILL_REFERENCED, audit_detail=detail),
        )
    )
    payload = json.loads(response.body)
    assert payload["message"] == detail
    from app.common.operation_log.context import (
        get_request_error_message,
        get_request_reference_detail,
    )

    assert get_request_error_message(request) == STILL_REFERENCED
    assert get_request_reference_detail(request) == detail


@pytest.fixture
def logs_session_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    OperationLog.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(
        "app.services.settings.logs.service.DatabaseConfig.get_session_factory",
        lambda: factory,
    )
    monkeypatch.setattr(
        "app.services.settings.logs.service._schedule_ip_lookup",
        lambda _log_id, _client_ip: None,
    )
    try:
        yield factory
    finally:
        engine.dispose()


def test_operation_log_keeps_full_reference_detail(
    logs_session_factory: sessionmaker[Session],
) -> None:
    detail = "无法删除基地「芜湖」\n" + ("  - 有 1 条项目，请先处理这些项目\n" * 40)
    OperationLogService().record_from_request(
        user=None,
        method="DELETE",
        path="/api/masterdata/locations/wuhu",
        query_string="",
        status_code=400,
        client_ip=None,
        error_message=STILL_REFERENCED,
        reference_detail=detail,
    )
    db = logs_session_factory()
    try:
        row = db.query(OperationLog).one()
        assert row.error_message == STILL_REFERENCED
        assert row.detail is not None
        assert row.detail.startswith("无法删除基地「芜湖」")
        assert row.detail.count("请先处理这些项目") == 40
        assert len(row.detail) > 500
    finally:
        db.close()


def test_delete_request_shows_detail_and_writes_operation_log(
    logs_session_factory: sessionmaker[Session],
) -> None:
    app = FastAPI()
    app.add_middleware(OperationLogMiddleware)
    register_exception_handlers(app)

    @app.delete("/api/masterdata/locations/{location}")
    def delete_location(location: str) -> None:
        raise BusinessException(
            STILL_REFERENCED,
            audit_detail=(
                f"无法删除基地「{location}」，原因如下：\n"
                "  - 有 2 条项目，请先处理这些项目\n"
                "请处理完以上数据后再删除。"
            ),
        )

    response = TestClient(app).delete("/api/masterdata/locations/芜湖")
    body = response.json()
    assert response.status_code == 400
    assert "有 2 条项目，请先处理这些项目" in body["message"]
    assert "无法删除基地「芜湖」" in body["message"]
    assert body["data"] is None
    db = logs_session_factory()
    try:
        row = db.query(OperationLog).one()
        assert row.method == "DELETE"
        assert row.success is False
        assert row.error_message == STILL_REFERENCED
        assert row.detail is not None
        assert "有 2 条项目，请先处理这些项目" in row.detail
        assert "无法删除基地「芜湖」" in row.detail
    finally:
        db.close()
