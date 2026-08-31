"""冲压检具费：无工艺拒模板/上传、模板行数=去重零件、默认 0.8/10、覆盖写入、非法零件整单失败。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.config import settings
from app.database import Base
from app.exceptions.base import BusinessException, NotFoundException
from app.models.file_trace.upload_file import UploadFile
from app.models.stamping.die import StampingDiePart
from app.models.stamping.gauge_fee import (
    DEFAULT_ALLOCATION_QTY,
    DEFAULT_GAUGE_FEE,
    STATUS_EFFECTIVE,
    StampingGaugeFee,
)
from app.models.stamping.part import StampingPart
from app.parsers.stamping.gauge_fee_parser import (
    HEADER_ALLOCATION_QTY,
    HEADER_GAUGE_FEE,
    HEADER_PART_NAME,
    HEADER_PART_NUMBER,
    HEADER_STATUS,
    parse_gauge_fee_excel,
)
from app.schemas.dto.stamping_gauge_fee_dto import StampingGaugeFeeQuery, StampingGaugeFeeUpdate
from app.services.stamping.gauge_fee.export_service import StampingGaugeFeeExportService
from app.services.stamping.gauge_fee.gauge_fee_service import StampingGaugeFeeService
from app.services.stamping.gauge_fee.upload_service import StampingGaugeFeeUploadService

LOCATION = "芜湖"
VEHICLE = "T13J"


@pytest.fixture
def memory_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "UPLOAD_DIR", upload_dir)

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            StampingPart.__table__,
            StampingDiePart.__table__,
            StampingGaugeFee.__table__,
            UploadFile.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _add_part(
    db: Session,
    *,
    part_number: str,
    part_name: str,
    version: str = "V1",
) -> None:
    db.add(
        StampingPart(
            location=LOCATION,
            vehicle_model=VEHICLE,
            version=version,
            part_number=part_number,
            part_name=part_name,
            excel_filename="T13J工艺确认表.xlsx",
        )
    )
    db.commit()


def _excel_bytes(rows: list[tuple[object, object, object, object, object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            HEADER_PART_NUMBER,
            HEADER_PART_NAME,
            HEADER_GAUGE_FEE,
            HEADER_ALLOCATION_QTY,
            HEADER_STATUS,
        ]
    )
    for row in rows:
        sheet.append(list(row))
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _add_die_part(
    db: Session,
    *,
    part_number: str,
    part_name: str,
    seq_no: int | None = None,
) -> None:
    db.add(
        StampingDiePart(
            location=LOCATION,
            vehicle_model=VEHICLE,
            part_number=part_number,
            part_name=part_name,
            seq_no=seq_no,
            excel_filename="模具布点.xlsx",
        )
    )
    db.commit()


def test_template_rejected_without_die(memory_db: Session) -> None:
    upload = StampingGaugeFeeUploadService()
    _add_part(memory_db, part_number="P001", part_name="仅工艺")
    with pytest.raises(BusinessException, match="没有模具布点"):
        upload.build_template(memory_db, location=LOCATION, vehicle_model=VEHICLE)


def test_upload_rejected_without_die(memory_db: Session) -> None:
    upload = StampingGaugeFeeUploadService()
    content = _excel_bytes([("P001", "左前门内板", Decimal("0.8"), Decimal("10"), "生效")])
    with pytest.raises(BusinessException, match="没有模具布点"):
        upload.import_excel(
            memory_db,
            file_content=content,
            filename="检具费.xlsx",
            location=LOCATION,
            vehicle_model=VEHICLE,
            current_user=SYSTEM_USER,
        )


def test_template_rows_come_from_die_not_process(memory_db: Session) -> None:
    _add_part(memory_db, part_number="P001", part_name="工艺名")
    _add_part(memory_db, part_number="P002", part_name="工艺无模具")
    _add_die_part(memory_db, part_number="P001", part_name="模具名", seq_no=1)

    content, filename = StampingGaugeFeeUploadService().build_template(
        memory_db, location=LOCATION, vehicle_model=VEHICLE
    )
    assert VEHICLE in filename
    workbook = load_workbook(BytesIO(content), data_only=True)
    sheet = workbook.active
    data_rows = list(sheet.iter_rows(min_row=2, values_only=True))
    numbers = [str(row[0]) for row in data_rows if row[0]]
    assert numbers == ["P001"]
    assert data_rows[0][1] == "模具名"
    assert Decimal(str(data_rows[0][2])) == DEFAULT_GAUGE_FEE
    assert Decimal(str(data_rows[0][3])) == DEFAULT_ALLOCATION_QTY
    assert data_rows[0][4] == "生效"

    parsed = parse_gauge_fee_excel(content)
    assert parsed.errors == []
    assert len(parsed.rows) == 1
    assert parsed.rows[0].gauge_fee == DEFAULT_GAUGE_FEE
    assert parsed.rows[0].allocation_qty == DEFAULT_ALLOCATION_QTY
    assert parsed.rows[0].status == STATUS_EFFECTIVE


def test_import_overwrites_scope_and_rejects_unknown_part(memory_db: Session) -> None:
    _add_die_part(memory_db, part_number="P001", part_name="模具名称")
    _add_die_part(memory_db, part_number="P002", part_name="第二件")
    upload = StampingGaugeFeeUploadService()
    list_service = StampingGaugeFeeService()

    first = upload.import_excel(
        memory_db,
        file_content=_excel_bytes(
            [
                ("P001", "Excel 旧名", Decimal("0.8"), Decimal("10"), "生效"),
                ("P002", "第二件", Decimal("0.8"), Decimal("10"), "生效"),
            ]
        ),
        filename="检具费-v1.xlsx",
        location=LOCATION,
        vehicle_model=VEHICLE,
        current_user=SYSTEM_USER,
    )
    assert first.imported_count == 2

    second = upload.import_excel(
        memory_db,
        file_content=_excel_bytes(
            [
                ("P001", "Excel 忽略", Decimal("1.2500"), Decimal("12"), "失效"),
            ]
        ),
        filename="检具费-v2.xlsx",
        location=LOCATION,
        vehicle_model=VEHICLE,
        current_user=SYSTEM_USER,
    )
    assert second.imported_count == 1

    items, total, filters = list_service.paginate(
        memory_db,
        StampingGaugeFeeQuery(location=LOCATION, vehicle_model=VEHICLE, page=1, size=20),
    )
    assert total == 1
    assert items[0].part_number == "P001"
    assert items[0].part_name == "模具名称"
    assert items[0].gauge_fee == Decimal("1.2500")
    assert items[0].allocation_qty == Decimal("12.0000")
    assert items[0].status == "invalid"
    assert filters.summary.total_count == 1
    assert filters.summary.invalid_count == 1
    assert filters.summary.effective_count == 0
    assert filters.summary.total_gauge_fee == Decimal("1.2500")

    with pytest.raises(BusinessException, match="不在该基地\\+项目模具布点"):
        upload.import_excel(
            memory_db,
            file_content=_excel_bytes(
                [
                    ("P001", "工艺名称", Decimal("0.8"), Decimal("10"), "生效"),
                    ("UNKNOWN99", "幽灵件", Decimal("0.8"), Decimal("10"), "生效"),
                ]
            ),
            filename="检具费-非法.xlsx",
            location=LOCATION,
            vehicle_model=VEHICLE,
            current_user=SYSTEM_USER,
        )
    items_after, total_after, _filters_after = list_service.paginate(
        memory_db,
        StampingGaugeFeeQuery(location=LOCATION, vehicle_model=VEHICLE, page=1, size=20),
    )
    assert total_after == 1
    assert items_after[0].gauge_fee == Decimal("1.2500")


def test_update_and_delete_single_row(memory_db: Session) -> None:
    _add_die_part(memory_db, part_number="P001", part_name="模具名称")
    upload = StampingGaugeFeeUploadService()
    service = StampingGaugeFeeService()
    upload.import_excel(
        memory_db,
        file_content=_excel_bytes([("P001", "工艺名称", Decimal("0.8"), Decimal("10"), "生效")]),
        filename="检具费.xlsx",
        location=LOCATION,
        vehicle_model=VEHICLE,
        current_user=SYSTEM_USER,
    )
    items, _total, _filters = service.paginate(
        memory_db,
        StampingGaugeFeeQuery(location=LOCATION, vehicle_model=VEHICLE, page=1, size=20),
    )
    record_id = items[0].id
    updated = service.update(
        memory_db,
        record_id,
        StampingGaugeFeeUpdate(
            gauge_fee=Decimal("1.1000"),
            allocation_qty=Decimal("8"),
            status="invalid",
        ),
        current_user=SYSTEM_USER,
    )
    assert updated.gauge_fee == Decimal("1.1000")
    assert updated.allocation_qty == Decimal("8.0000")
    assert updated.status == "invalid"
    assert updated.part_number == "P001"

    service.delete(memory_db, record_id)
    with pytest.raises(NotFoundException):
        service.delete(memory_db, record_id)


def test_parse_rejects_empty_or_negative_money() -> None:
    empty_result = parse_gauge_fee_excel(
        _excel_bytes([("P001", "名称", None, Decimal("10"), "生效")])
    )
    assert empty_result.rows == []
    assert any("检具费" in msg and "不能为空" in msg for msg in empty_result.errors)

    empty_qty = parse_gauge_fee_excel(
        _excel_bytes([("P001", "名称", Decimal("0.8"), None, "生效")])
    )
    assert empty_qty.rows == []
    assert any("分摊" in msg and "不能为空" in msg for msg in empty_qty.errors)

    negative_fee = parse_gauge_fee_excel(
        _excel_bytes([("P001", "名称", Decimal("-0.1"), Decimal("10"), "生效")])
    )
    assert negative_fee.rows == []
    assert any("不能为负" in msg for msg in negative_fee.errors)

    negative_qty = parse_gauge_fee_excel(
        _excel_bytes([("P001", "名称", Decimal("0.8"), Decimal("-1"), "生效")])
    )
    assert negative_qty.rows == []
    assert any("正整数" in msg for msg in negative_qty.errors)

    fraction_qty = parse_gauge_fee_excel(
        _excel_bytes([("P001", "名称", Decimal("0.8"), Decimal("10.5"), "生效")])
    )
    assert fraction_qty.rows == []
    assert any("正整数" in msg for msg in fraction_qty.errors)


def test_export_includes_location_and_vehicle(memory_db: Session) -> None:
    _add_die_part(memory_db, part_number="P001", part_name="左前门内板")
    StampingGaugeFeeUploadService().import_excel(
        memory_db,
        file_content=_excel_bytes(
            [("P001", "左前门内板", Decimal("0.8000"), Decimal("10"), "生效")]
        ),
        filename="检具费.xlsx",
        location=LOCATION,
        vehicle_model=VEHICLE,
        current_user=SYSTEM_USER,
    )
    content, filename = StampingGaugeFeeExportService().export(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE,
        part_number=None,
        status=None,
        current_user=SYSTEM_USER,
    )
    assert LOCATION in filename
    assert VEHICLE in filename
    workbook = load_workbook(BytesIO(content))
    sheet = workbook.active
    headers = [cell.value for cell in sheet[4]]
    assert headers[:7] == [
        "基地",
        "项目",
        "零件号",
        "零件名称",
        "检具费（万元）",
        "项目分摊数量（万台）",
        "状态",
    ]
    assert sheet.cell(row=5, column=1).value == LOCATION
    assert sheet.cell(row=5, column=2).value == VEHICLE
    assert sheet.cell(row=5, column=3).value == "P001"
    assert sheet.cell(row=5, column=4).value == "左前门内板"
    assert Decimal(str(sheet.cell(row=5, column=5).value)) == Decimal("0.8000")
    assert Decimal(str(sheet.cell(row=5, column=6).value)) == Decimal("10.0000")
    assert sheet.cell(row=5, column=7).value == "生效"
    assert "基地" in str(sheet.cell(row=2, column=1).value)
    assert "项目" in str(sheet.cell(row=2, column=1).value)
