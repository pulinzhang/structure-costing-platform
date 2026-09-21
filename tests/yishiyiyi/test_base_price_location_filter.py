"""基准价宽表只导入已启用基地；其它表头列是噪声。"""

from __future__ import annotations

from collections.abc import Generator
from io import BytesIO

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.masterdata.location import Location, LocationAlias
from app.parsers.yishiyiyi.base_price.steel_base_price_parser import (
    parse_base_price_excel,
)
from app.schemas.dto.location_dto import LocationUpdateDTO
from app.services.masterdata.location.service import LocationService
from tests.masterdata.location_fixtures import insert_sample_locations


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
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _wide_table_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet["A1"] = "2025年1月"
    sheet["A4"] = "序号"
    sheet["B4"] = "钢种"
    sheet["C4"] = "牌号"
    sheet["E4"] = "参考规格"
    sheet["F4"] = "芜湖基地"
    sheet["H4"] = "青岛基地"
    sheet["F5"] = "中标钢厂"
    sheet["G5"] = "到厂原卷承兑价格"
    sheet["H5"] = "中标钢厂"
    sheet["I5"] = "到厂原卷承兑价格"
    sheet["A6"] = 1
    sheet["B6"] = "冷轧"
    sheet["C6"] = "DC01"
    sheet["E6"] = "1.0*1250"
    sheet["F6"] = "马钢"
    sheet["G6"] = 5000
    sheet["H6"] = "本钢"
    sheet["I6"] = 5100
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_lookup_only_includes_enabled_locations(memory_db: Session) -> None:
    from app.common.audit import SYSTEM_USER

    insert_sample_locations(memory_db)
    LocationService().update(
        memory_db,
        "芜湖",
        LocationUpdateDTO(is_enabled=False),
        current_user=SYSTEM_USER,
    )
    lookup = LocationService().enabled_name_lookup(memory_db)
    assert lookup["青岛"] == "青岛"
    assert lookup["青岛基地"] == "青岛"
    assert "芜湖" not in lookup
    assert "芜湖基地" not in lookup


def test_parser_keeps_only_enabled_location_columns() -> None:
    lookup = {"青岛": "青岛", "青岛基地": "青岛"}
    parsed = parse_base_price_excel(_wide_table_bytes(), location_lookup=lookup)
    assert not parsed.errors
    locations = {str(row["location"]) for row in parsed.records}
    mills = {str(row["steel_mill"]) for row in parsed.records}
    assert locations == {"青岛"}
    assert mills == {"本钢"}
    assert any("芜湖基地" in warning for warning in parsed.warnings)


def test_parser_errors_when_no_enabled_column_matches() -> None:
    lookup = {"合肥": "合肥", "合肥基地": "合肥"}
    parsed = parse_base_price_excel(_wide_table_bytes(), location_lookup=lookup)
    assert parsed.errors
    assert parsed.records == []
    assert any("已跳过" in error for error in parsed.errors)
