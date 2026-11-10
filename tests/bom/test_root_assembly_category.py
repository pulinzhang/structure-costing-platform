"""材料清单根节点的总成分类只认启用的主数据。"""

from __future__ import annotations

from collections.abc import Generator
from io import BytesIO

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.exceptions.base import BusinessException
from app.models.masterdata.assembly_category import AssemblyCategory
from app.parsers.bom.bom_parser import parse_bom_excel
from app.services.bom.bom.upload.gates.category import bind_root_assembly_categories
from app.services.masterdata.assembly_category.service import AssemblyCategoryService


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

    Base.metadata.create_all(bind=engine, tables=[AssemblyCategory.__table__])
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _workbook(*, category: str | None, include_column: bool = True) -> bytes:
    workbook = Workbook()
    sheet = workbook.worksheets[0]
    sheet.cell(1, 2, "总成零件内部号")
    sheet.cell(1, 3, "总成零件号")
    sheet.cell(1, 9, "一级零件号")
    if include_column:
        sheet.cell(1, 24, "总成分类")
    sheet.cell(2, 1, 1)
    sheet.cell(2, 3, "501000001AA")
    sheet.cell(2, 9, "502000001AA")
    if include_column and category is not None:
        sheet.cell(2, 24, category)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_parser_reads_category_on_the_root_only() -> None:
    parsed = parse_bom_excel(_workbook(category="总成件"))
    roots = [node for node in parsed.nodes if node.level == 0]
    children = [node for node in parsed.nodes if node.level != 0]
    assert [node.assembly_category_label for node in roots] == ["总成件"]
    assert all(node.assembly_category_label is None for node in children)


def test_parser_without_the_column_leaves_the_root_blank() -> None:
    parsed = parse_bom_excel(_workbook(category=None, include_column=False))
    root = next(node for node in parsed.nodes if node.level == 0)
    assert root.assembly_category_label is None


def test_import_accepts_enabled_name_or_code(memory_db: Session) -> None:
    AssemblyCategoryService().ensure_seed_if_empty(memory_db)
    by_name = parse_bom_excel(_workbook(category="冲压件"))
    bind_root_assembly_categories(memory_db, by_name.nodes, required=True)
    stamped = next(node for node in by_name.nodes if node.level == 0)
    assert stamped.assembly_category_id is not None

    by_code = parse_bom_excel(_workbook(category="black_paint"))
    bind_root_assembly_categories(memory_db, by_code.nodes, required=True)
    painted = next(node for node in by_code.nodes if node.level == 0)
    assert painted.assembly_category_id != stamped.assembly_category_id


def test_import_rejects_blank_or_unknown_category(memory_db: Session) -> None:
    AssemblyCategoryService().ensure_seed_if_empty(memory_db)
    blank = parse_bom_excel(_workbook(category=None))
    with pytest.raises(BusinessException, match="总成分类") as blank_error:
        bind_root_assembly_categories(memory_db, blank.nodes, required=True)
    assert "整本未导入" in str(blank_error.value)

    unknown = parse_bom_excel(_workbook(category="其他件"))
    with pytest.raises(BusinessException, match="不在启用分类里"):
        bind_root_assembly_categories(memory_db, unknown.nodes, required=True)


def test_change_file_without_the_column_is_left_alone(memory_db: Session) -> None:
    parsed = parse_bom_excel(_workbook(category=None, include_column=False))
    bind_root_assembly_categories(memory_db, parsed.nodes, required=False)
    root = next(node for node in parsed.nodes if node.level == 0)
    assert root.assembly_category_id is None
