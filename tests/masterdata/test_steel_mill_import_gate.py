"""导入整本退回：基准价带 Excel 行，加减价带 sheet。"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.exceptions.base import BusinessException
from app.models.masterdata.steel_mill import SteelMill, SteelMillAlias
from app.schemas.dto.steel_mill_dto import SteelMillCreate, SteelMillUpdate
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.steel_mill.service import SteelMillService

_USER = UserVO(id=1, username="admin")


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
        tables=[SteelMill.__table__, SteelMillAlias.__table__],
    )
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_missing_mills_cite_excel_row_and_sheet(memory_db: Session) -> None:
    service = SteelMillService()
    with pytest.raises(BusinessException) as base_error:
        service.require_enabled_many(
            memory_db,
            ["华菱", "华菱", "未知厂"],
            places=["基准价，Excel 第12行", "基准价，Excel 第30行", "基准价，Excel 第18行"],
        )
    assert str(base_error.value) == (
        "钢厂「华菱」不存在（基准价，Excel 第12行）；"
        "钢厂「未知厂」不存在（基准价，Excel 第18行）。"
        "请到钢厂页手工增加（#/steel-mill）。本文件未写入。"
    )

    with pytest.raises(BusinessException) as policy_error:
        service.require_enabled_many(
            memory_db,
            ["首钢最新"],
            places=["加减价，sheet「首钢最新」"],
        )
    assert "钢厂「首钢最新」不存在（加减价，sheet「首钢最新」）" in str(policy_error.value)
    assert str(policy_error.value).endswith("请到钢厂页手工增加（#/steel-mill）。本文件未写入。")


def test_disabled_mill_cites_place_and_abbreviation(memory_db: Session) -> None:
    service = SteelMillService()
    created = service.create(
        memory_db,
        SteelMillCreate(
            abbreviation="首钢",
            full_name="首钢",
            aliases=["首钢最新", "首钢(新)"],
        ),
        _USER,
    )
    service.update(
        memory_db,
        created.id,
        SteelMillUpdate(
            abbreviation="首钢",
            full_name="首钢",
            is_enabled=False,
            aliases=["首钢最新", "首钢(新)"],
        ),
        _USER,
    )
    with pytest.raises(BusinessException) as disabled:
        service.require_enabled_many(
            memory_db,
            ["首钢最新", "首钢(新)"],
            places=["加减价，sheet「首钢最新」", "加减价，sheet「首钢(新)」"],
        )
    assert str(disabled.value) == (
        "钢厂「首钢」已停用，不能再选用（加减价，sheet「首钢最新」）。"
        "请到钢厂页启用（#/steel-mill）。本文件未写入。"
    )


def test_empty_mill_uses_the_same_sentence(memory_db: Session) -> None:
    service = SteelMillService()
    with pytest.raises(BusinessException) as error:
        service.require_enabled_many(
            memory_db,
            ["", "华菱"],
            places=["基准价，Excel 第4行", "基准价，Excel 第12行"],
        )
    assert str(error.value) == (
        "钢厂不能为空（基准价，Excel 第4行）；"
        "钢厂「华菱」不存在（基准价，Excel 第12行）。"
        "请到钢厂页手工增加（#/steel-mill）。本文件未写入。"
    )


def test_more_than_twenty_mills_keep_the_count(memory_db: Session) -> None:
    service = SteelMillService()
    names = [f"厂{index:02d}" for index in range(1, 22)]
    places = [f"基准价，Excel 第{index}行" for index in range(1, 22)]
    with pytest.raises(BusinessException) as error:
        service.require_enabled_many(memory_db, names, places=places)
    message = str(error.value)
    assert "钢厂「厂01」不存在（基准价，Excel 第1行）" in message
    assert "钢厂「厂20」不存在（基准价，Excel 第20行）" in message
    assert "厂21" not in message
    assert "共 21 家" in message
    assert message.endswith("请到钢厂页手工增加（#/steel-mill）。本文件未写入。")
