"""操作日志按客户端 IP 过滤。"""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.settings.operation_log import OperationLog
from app.repositories.settings.logs.operation_log_repository import (
    OperationLogRepository,
)
from app.schemas.dto.operation_log_dto import OperationLogCreate


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    OperationLog.__table__.create(engine)
    return sessionmaker(bind=engine)()


def _row(client_ip: str) -> OperationLogCreate:
    return OperationLogCreate(
        method="POST",
        path="/api/auth/login",
        action="登录",
        summary="登录",
        client_ip=client_ip,
    )


def test_paginate_and_export_filter_client_ip() -> None:
    db = _session()
    try:
        repository = OperationLogRepository()
        repository.create(db, _row("10.1.2.3"))
        repository.create(db, _row("192.168.0.8"))
        db.commit()

        rows, total = repository.paginate(db, client_ip="10.1")
        assert total == 1
        assert rows[0].client_ip == "10.1.2.3"

        blank_rows, blank_total = repository.paginate(db, client_ip="   ")
        assert blank_total == 2
        assert len(blank_rows) == 2

        exported = repository.list_for_export(db, client_ip="192.168.0.8")
        assert [row.client_ip for row in exported] == ["192.168.0.8"]
    finally:
        db.close()
