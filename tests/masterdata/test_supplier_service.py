"""供应商主数据：无种子、命名空间互斥、启用门禁、别名展开、Excel 整单事务。"""

from __future__ import annotations

import inspect
from collections.abc import Generator
from io import BytesIO

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.supplier import Supplier, SupplierAlias
from app.schemas.dto.supplier_dto import (
    SupplierAliasCreateDTO,
    SupplierCreateDTO,
    SupplierUpdateDTO,
)
from app.services.masterdata.supplier import SupplierService


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
        tables=[Supplier.__table__, SupplierAlias.__table__],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _create(
    service: SupplierService,
    db: Session,
    *,
    abbreviation: str = "常庆",
    full_name: str = "安庆常庆汽车部件有限公司",
    erp_code: str = "CQ001",
    aliases: list[str] | None = None,
):
    return service.create(
        db,
        SupplierCreateDTO(
            abbreviation=abbreviation,
            full_name=full_name,
            erp_code=erp_code,
            aliases=aliases or [],
        ),
        current_user=SYSTEM_USER,
    )


def _excel_bytes(rows: list[tuple[str, str, str, str]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["缩写", "全称", "ERP 代码", "别名"])
    for row in rows:
        sheet.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_no_seed_method_and_empty_table(memory_db: Session) -> None:
    service = SupplierService()
    assert not hasattr(service, "ensure_seed_if_empty")
    assert service.repository.list_all(memory_db) == []
    assert service.list_registered(memory_db) == []


def test_create_records_canonical_and_alias(memory_db: Session) -> None:
    service = SupplierService()
    vo = _create(service, memory_db, aliases=["常庆汽配"])
    assert vo.full_name == "安庆常庆汽车部件有限公司"
    assert vo.abbreviation == "常庆"
    assert vo.erp_code == "CQ001"
    assert vo.aliases == ["常庆汽配"]
    assert vo.is_enabled is True
    assert service.resolve_canonical(memory_db, "常庆汽配") == vo.full_name
    assert service.resolve_canonical(memory_db, "常庆") == vo.full_name
    assert service.resolve_canonical(memory_db, "CQ001") == vo.full_name


def test_create_duplicate_full_name_raises(memory_db: Session) -> None:
    service = SupplierService()
    _create(service, memory_db)
    with pytest.raises(BusinessException, match="该全称已有供应商"):
        _create(service, memory_db, abbreviation="常庆二", erp_code="CQ002")


def test_namespace_is_mutually_exclusive(memory_db: Session) -> None:
    service = SupplierService()
    _create(service, memory_db, aliases=["常庆汽配"])
    with pytest.raises(BusinessException, match="该全称已有供应商"):
        _create(
            service,
            memory_db,
            abbreviation="别厂",
            full_name="常庆汽配",
            erp_code="OT001",
        )
    with pytest.raises(BusinessException, match="该缩写已被占用"):
        _create(
            service,
            memory_db,
            abbreviation="常庆",
            full_name="另一家冲压有限公司",
            erp_code="OT002",
        )
    with pytest.raises(BusinessException, match="该 ERP 代码已被占用"):
        _create(
            service,
            memory_db,
            abbreviation="别厂",
            full_name="另一家冲压有限公司",
            erp_code="CQ001",
        )
    with pytest.raises(BusinessException, match="别名不得等于"):
        service.add_alias(
            memory_db,
            "安庆常庆汽车部件有限公司",
            SupplierAliasCreateDTO(alias="常庆"),
            current_user=SYSTEM_USER,
        )


def test_identity_fields_must_be_distinct(memory_db: Session) -> None:
    service = SupplierService()
    with pytest.raises(BusinessException, match="缩写、全称、ERP 代码与别名不得相同"):
        _create(
            service,
            memory_db,
            abbreviation="常庆",
            full_name="常庆",
            erp_code="CQ001",
        )


def test_require_enabled_fails_when_missing_or_disabled(memory_db: Session) -> None:
    service = SupplierService()
    with pytest.raises(BusinessException, match="没有该供应商"):
        service.require_enabled(memory_db, "安庆常庆汽车部件有限公司")
    _create(service, memory_db, aliases=["常庆汽配"])
    assert service.require_enabled(memory_db, "常庆汽配") == "安庆常庆汽车部件有限公司"
    service.update(
        memory_db,
        "安庆常庆汽车部件有限公司",
        SupplierUpdateDTO(is_enabled=False),
        current_user=SYSTEM_USER,
    )
    with pytest.raises(BusinessException, match="供应商已禁用"):
        service.require_enabled(memory_db, "安庆常庆汽车部件有限公司")
    with pytest.raises(BusinessException, match="供应商已禁用"):
        service.require_enabled(memory_db, "常庆")


def test_expand_for_query_includes_short_codes_and_aliases(memory_db: Session) -> None:
    service = SupplierService()
    _create(service, memory_db, aliases=["常庆汽配", "安庆常庆"])
    names = service.expand_for_query(memory_db, "常庆汽配")
    assert names[0] == "安庆常庆汽车部件有限公司"
    assert "常庆" in names
    assert "CQ001" in names
    assert "常庆汽配" in names
    assert "安庆常庆" in names
    assert service.expand_for_query(memory_db, "不存在的厂") == []
    assert service.resolve_canonical(memory_db, "不存在的厂") is None


def test_excel_skips_existing_full_name(memory_db: Session) -> None:
    service = SupplierService()
    _create(service, memory_db)
    result = service.process_upload(
        memory_db,
        file_content=_excel_bytes([("常庆", "安庆常庆汽车部件有限公司", "CQ001", "常庆汽配")]),
        current_user=SYSTEM_USER,
    )
    assert result.created_count == 0
    assert result.skipped_count == 1
    refreshed = service.repository.get_by_full_name(memory_db, "安庆常庆汽车部件有限公司")
    assert refreshed is not None
    assert refreshed.aliases == []


def test_excel_duplicate_signature_in_file_is_skipped(memory_db: Session) -> None:
    service = SupplierService()
    result = service.process_upload(
        memory_db,
        file_content=_excel_bytes(
            [
                ("常庆", "安庆常庆汽车部件有限公司", "CQ001", "常庆汽配"),
                ("常庆", "安庆常庆汽车部件有限公司", "CQ001", "常庆汽配"),
            ]
        ),
        current_user=SYSTEM_USER,
    )
    assert result.created_count == 1
    assert result.skipped_count == 1


def test_excel_conflict_rolls_back_whole_file(memory_db: Session) -> None:
    service = SupplierService()
    with pytest.raises(BusinessException, match="冲突"):
        service.process_upload(
            memory_db,
            file_content=_excel_bytes(
                [
                    ("常庆", "安庆常庆汽车部件有限公司", "CQ001", ""),
                    ("常庆", "另一家冲压有限公司", "OT001", ""),
                ]
            ),
            current_user=SYSTEM_USER,
        )
    assert service.repository.list_all(memory_db) == []


def test_excel_occupied_abbreviation_in_db_fails(memory_db: Session) -> None:
    service = SupplierService()
    _create(service, memory_db)
    with pytest.raises(BusinessException, match="该缩写已被占用"):
        service.process_upload(
            memory_db,
            file_content=_excel_bytes([("常庆", "另一家冲压有限公司", "OT001", "")]),
            current_user=SYSTEM_USER,
        )
    assert service.repository.get_by_full_name(memory_db, "另一家冲压有限公司") is None


def test_parser_does_not_import_supplier_service() -> None:
    from app.parsers.masterdata import supplier_parser

    source = inspect.getsource(supplier_parser)
    assert "SupplierService" not in source
    assert "app.services.masterdata" not in source


def test_supplier_service_does_not_import_downstream() -> None:
    from app.services.masterdata.supplier import supplier_service

    source = inspect.getsource(supplier_service)
    assert "app.services.stamping" not in source
    assert "app.services.bom" not in source
    assert "app.services.costing" not in source


def test_rename_full_name_keeps_old_as_alias(memory_db: Session) -> None:
    service = SupplierService()
    _create(service, memory_db, aliases=["常庆汽配"])
    updated = service.update(
        memory_db,
        "安庆常庆汽车部件有限公司",
        SupplierUpdateDTO(full_name="安庆常庆汽车部件有限公司新名"),
        current_user=SYSTEM_USER,
    )
    assert updated.full_name == "安庆常庆汽车部件有限公司新名"
    assert "安庆常庆汽车部件有限公司" in updated.aliases
    assert "常庆汽配" in updated.aliases


def test_rename_to_own_alias(memory_db: Session) -> None:
    service = SupplierService()
    _create(service, memory_db, aliases=["常庆汽配"])
    updated = service.update(
        memory_db,
        "安庆常庆汽车部件有限公司",
        SupplierUpdateDTO(full_name="常庆汽配"),
        current_user=SYSTEM_USER,
    )
    assert updated.full_name == "常庆汽配"
    assert "安庆常庆汽车部件有限公司" in updated.aliases
    assert "常庆汽配" not in updated.aliases


def test_delete_unreferenced_supplier(memory_db: Session) -> None:
    service = SupplierService()
    _create(service, memory_db)
    service.delete(memory_db, "安庆常庆汽车部件有限公司")
    with pytest.raises(NotFoundException):
        service.update(
            memory_db,
            "安庆常庆汽车部件有限公司",
            SupplierUpdateDTO(is_enabled=False),
            current_user=SYSTEM_USER,
        )
