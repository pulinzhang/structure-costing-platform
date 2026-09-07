"""基地主数据：命名空间互斥、空表种子、启用门禁、别名展开、删除文案、Parser 隔离。"""

from __future__ import annotations

import inspect
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.exceptions.base import BusinessException
from app.models.masterdata.location import Location, LocationAlias
from app.schemas.dto.location_dto import (
    LocationAliasCreateDTO,
    LocationCreateDTO,
    LocationUpdateDTO,
)
from app.services.masterdata.location import LocationService


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
        tables=[Location.__table__, LocationAlias.__table__],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_ensure_seed_if_empty(memory_db: Session) -> None:
    service = LocationService()
    assert service.repository.count(memory_db) == 0
    service.ensure_seed_if_empty(memory_db)
    names = service.list_registered(memory_db)
    assert names == ["大连", "芜湖", "鄂尔多斯", "青岛"]
    service.ensure_seed_if_empty(memory_db)
    assert service.list_registered(memory_db) == names
    assert "青岛基地" in service.expand_for_query(memory_db, "青岛")


def test_create_records_canonical_and_alias(memory_db: Session) -> None:
    service = LocationService()
    vo = service.create(
        memory_db,
        LocationCreateDTO(location="福州", aliases=["福州基地"]),
        current_user=SYSTEM_USER,
    )
    assert vo.location == "福州"
    assert vo.aliases == ["福州基地"]
    assert service.resolve_canonical(memory_db, "福州基地") == "福州"
    two = service.create(
        memory_db,
        LocationCreateDTO(location="西安", aliases=["西安基地", "西安厂"]),
        current_user=SYSTEM_USER,
    )
    assert two.aliases == ["西安基地", "西安厂"]
    assert service.resolve_canonical(memory_db, "西安厂") == "西安"
    with pytest.raises(BusinessException, match="别名不得与规范名相同"):
        service.create(
            memory_db,
            LocationCreateDTO(location="合肥", aliases=["合肥"]),
            current_user=SYSTEM_USER,
        )


def test_canonical_and_alias_are_mutually_exclusive(memory_db: Session) -> None:
    service = LocationService()
    service.ensure_seed_if_empty(memory_db)
    with pytest.raises(BusinessException, match="规范名不得等于已有别名"):
        service.create(
            memory_db,
            LocationCreateDTO(location="青岛基地", aliases=["青岛厂"]),
            current_user=SYSTEM_USER,
        )
    with pytest.raises(BusinessException, match="别名不得等于已有规范名"):
        service.add_alias(
            memory_db,
            "青岛",
            LocationAliasCreateDTO(alias="大连"),
            current_user=SYSTEM_USER,
        )


def test_require_enabled_fails_when_disabled(memory_db: Session) -> None:
    service = LocationService()
    service.ensure_seed_if_empty(memory_db)
    service.update(
        memory_db,
        "青岛",
        LocationUpdateDTO(is_enabled=False),
        current_user=SYSTEM_USER,
    )
    with pytest.raises(BusinessException, match="基地已禁用"):
        service.require_enabled(memory_db, "青岛")
    with pytest.raises(BusinessException, match="基地已禁用"):
        service.require_enabled(memory_db, "青岛基地")
    assert service.require_enabled(memory_db, "芜湖") == "芜湖"


def test_expand_for_query_includes_canonical(memory_db: Session) -> None:
    service = LocationService()
    service.ensure_seed_if_empty(memory_db)
    names = service.expand_for_query(memory_db, "青岛基地")
    assert names[0] == "青岛"
    assert "青岛基地" in names
    assert service.expand_for_query(memory_db, "青岛厂") == []
    assert service.resolve_canonical(memory_db, "青岛厂") is None


def test_delete_integrity_error_message(memory_db: Session) -> None:
    service = LocationService()
    service.ensure_seed_if_empty(memory_db)

    def _raise_integrity(*_args: object, **_kwargs: object) -> None:
        raise IntegrityError("DELETE", {}, Exception("fk"))

    service.repository.delete = MagicMock(side_effect=_raise_integrity)  # type: ignore[method-assign]
    with pytest.raises(BusinessException, match="仍被引用，不能删除"):
        service.delete(memory_db, "青岛")


def test_parser_does_not_import_location_service() -> None:
    from app.parsers.yishiyiyi.base_price import steel_base_price_parser

    source = inspect.getsource(steel_base_price_parser)
    assert "LocationService" not in source
    assert "app.services.masterdata" not in source


def test_llm_scope_expands_aliases_not_unregistered(memory_db: Session) -> None:
    from app.repositories.llm.scope_options_repository import ScopeOptionsRepository

    LocationService().ensure_seed_if_empty(memory_db)
    repo = ScopeOptionsRepository()
    names = repo.expand_location_names(memory_db, "青岛基地")
    assert names[0] == "青岛"
    assert "青岛基地" in names
    assert repo.expand_location_names(memory_db, "青岛厂") == []
    assert "青岛厂" not in repo.location_alias_map(memory_db)


def test_llm_analysis_does_not_import_location_service() -> None:
    import app.repositories.llm.annual_part_price_analysis_repository as annual_mod
    import app.repositories.llm.base_price_analysis_repository as base_price_mod
    import app.repositories.llm.bom_material_analysis_repository as bom_mod
    import app.repositories.llm.location_in as location_in_mod
    import app.repositories.llm.scope_options_repository as scope_mod
    import app.services.llm.query.entity_aligner as aligner_mod

    for module in (
        annual_mod,
        base_price_mod,
        bom_mod,
        location_in_mod,
        scope_mod,
        aligner_mod,
    ):
        source = inspect.getsource(module)
        assert "from app.services.masterdata" not in source
        assert "import LocationService" not in source
