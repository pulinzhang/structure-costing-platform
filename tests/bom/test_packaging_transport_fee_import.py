"""BOM 包装运输费 — 解析器 / 导入单元测试。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, SYSTEM_USER
from app.config import settings
from app.database import Base
from app.exceptions.base import BusinessException
from app.models.bom.node import BomSnapshot
from app.models.bom.packaging_transport_fee import BomPackagingTransportFee
from app.models.file_trace.upload_file import UploadFile
from app.parsers.bom.packaging_transport_fee_parser import (
    parse_packaging_transport_fee_excel,
)
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
)
from app.services.bom.packaging_transport_fee.import_service import (
    BomPackagingTransportFeeImportService,
)

SAMPLE_XLSX = Path(__file__).resolve().parents[2] / "excel_sample" / "包装运输费用.xlsx"

LOCATION = "青岛"
YEAR = 2025
VEHICLE_MODEL = "T28"


@pytest.fixture
def sample_xlsx_bytes() -> bytes:
    if not SAMPLE_XLSX.exists():
        pytest.skip(f"样例文件不存在: {SAMPLE_XLSX}")
    return SAMPLE_XLSX.read_bytes()


@pytest.fixture
def memory_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Session, None, None]:
    """隔离内存库 + 临时上传目录，不写开发库。"""
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
            BomSnapshot.__table__,
            BomPackagingTransportFee.__table__,
            UploadFile.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    session.add(
        BomSnapshot(
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version="D/00",
            stage="initial",
            status="active",
            source_filename="fixture-bom.xlsx",
            created_by="system",
            updated_by="system",
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ---------------------------------------------------------------------------
# 解析器（纯函数）
# ---------------------------------------------------------------------------


class TestPackagingTransportFeeParser:
    def test_parse_sample_row_count(self, sample_xlsx_bytes: bytes) -> None:
        result = parse_packaging_transport_fee_excel(sample_xlsx_bytes)
        assert result.errors == []
        assert len(result.rows) == 84
        assert result.sheet_name

    def test_parse_sample_first_part_fees(self, sample_xlsx_bytes: bytes) -> None:
        result = parse_packaging_transport_fee_excel(sample_xlsx_bytes)
        row = next(r for r in result.rows if r.part_number == "501006870AA")
        assert row.part_name == "流水槽后部总成"
        assert row.packaging_type == "带轮料架"
        assert row.pieces_per_pack == 18
        assert row.unit_packaging_fee == Decimal("0.9800")
        assert row.unit_transport_fee == Decimal("1.5500")
        assert row.fixture_maint_fee == Decimal("0.4900")
        assert row.other_fee == Decimal("0.6994")
        assert row.packaging_transport_total == Decimal("3.7194")
        assert row.row_number >= 1

    def test_parse_empty_bytes(self) -> None:
        result = parse_packaging_transport_fee_excel(b"")
        assert result.rows == []
        assert result.errors == ["文件内容为空"]

    def test_parse_invalid_bytes(self) -> None:
        result = parse_packaging_transport_fee_excel(b"not-an-xlsx")
        assert result.rows == []
        assert result.errors
        assert "无法读取 Excel" in result.errors[0]

    def test_parse_platform_template(self) -> None:
        content, _filename = BomPackagingTransportFeeImportService().build_template()
        result = parse_packaging_transport_fee_excel(content)
        assert result.errors == []
        assert len(result.rows) >= 1
        assert result.rows[0].part_number == "501006870AA"
        assert result.rows[0].packaging_transport_total == Decimal("3.7194")


# ---------------------------------------------------------------------------
# 导入服务（内存库）
# ---------------------------------------------------------------------------


class TestPackagingTransportFeeImport:
    def test_import_creates_84_rows(self, memory_db: Session, sample_xlsx_bytes: bytes) -> None:
        service = BomPackagingTransportFeeImportService()
        result = service.import_excel(
            memory_db,
            file_content=sample_xlsx_bytes,
            filename="包装运输费用.xlsx",
            location=LOCATION,
            year=YEAR,
            vehicle_model=VEHICLE_MODEL,
            current_user=SYSTEM_USER,
        )
        assert result.created_count == 84
        assert result.updated_count == 0
        assert result.skipped_count == 0
        assert result.location == LOCATION
        assert result.year == YEAR
        assert result.vehicle_model == VEHICLE_MODEL
        assert result.source_filename == "包装运输费用.xlsx"
        archived_files = list(
            (settings.UPLOAD_DIR / "bom" / "packaging-transport-fee").rglob(
                "*_packaging-transport-fee_包装运输费用.xlsx"
            )
        )
        assert len(archived_files) >= 1
        assert archived_files[0].is_file()
        assert archived_files[0].stat().st_size == len(sample_xlsx_bytes)

        repo = BomPackagingTransportFeeRepository()
        rows = repo.list_by_scope(memory_db, LOCATION, YEAR, VEHICLE_MODEL)
        assert len(rows) == 84
        assert all(row.audit_status == AUDIT_PENDING for row in rows)

        first = repo.get_by_unique_key(memory_db, LOCATION, YEAR, VEHICLE_MODEL, "501006870AA")
        assert first is not None
        assert first.packaging_transport_total == Decimal("3.7194")
        assert first.unit_packaging_fee == Decimal("0.9800")
        assert first.unit_transport_fee == Decimal("1.5500")
        assert first.excel_filename == "包装运输费用.xlsx"
        assert first.sheet_name
        assert first.excel_row is not None and first.excel_row >= 1

    def test_import_rejects_without_bom(self, memory_db: Session, sample_xlsx_bytes: bytes) -> None:
        service = BomPackagingTransportFeeImportService()
        with pytest.raises(BusinessException, match="未找到材料清单"):
            service.import_excel(
                memory_db,
                file_content=sample_xlsx_bytes,
                filename="包装运输费用.xlsx",
                location="芜湖",
                year=YEAR,
                vehicle_model=VEHICLE_MODEL,
                current_user=SYSTEM_USER,
            )

    def test_reimport_updates_pending(self, memory_db: Session, sample_xlsx_bytes: bytes) -> None:
        service = BomPackagingTransportFeeImportService()
        service.import_excel(
            memory_db,
            file_content=sample_xlsx_bytes,
            filename="包装运输费用.xlsx",
            location=LOCATION,
            year=YEAR,
            vehicle_model=VEHICLE_MODEL,
            current_user=SYSTEM_USER,
        )
        result = service.import_excel(
            memory_db,
            file_content=sample_xlsx_bytes,
            filename="包装运输费用.xlsx",
            location=LOCATION,
            year=YEAR,
            vehicle_model=VEHICLE_MODEL,
            current_user=SYSTEM_USER,
        )
        assert result.created_count == 0
        assert result.updated_count == 84
        assert result.skipped_count == 0

    def test_import_skips_approved(self, memory_db: Session, sample_xlsx_bytes: bytes) -> None:
        service = BomPackagingTransportFeeImportService()
        service.import_excel(
            memory_db,
            file_content=sample_xlsx_bytes,
            filename="包装运输费用.xlsx",
            location=LOCATION,
            year=YEAR,
            vehicle_model=VEHICLE_MODEL,
            current_user=SYSTEM_USER,
        )
        repo = BomPackagingTransportFeeRepository()
        for row in repo.list_by_scope(memory_db, LOCATION, YEAR, VEHICLE_MODEL):
            row.audit_status = AUDIT_APPROVED
        memory_db.commit()
        memory_db.expire_all()

        result = service.import_excel(
            memory_db,
            file_content=sample_xlsx_bytes,
            filename="包装运输费用.xlsx",
            location=LOCATION,
            year=YEAR,
            vehicle_model=VEHICLE_MODEL,
            current_user=SYSTEM_USER,
        )
        assert result.created_count == 0
        assert result.updated_count == 0
        assert result.skipped_count == 84
        assert result.skipped_approved_count == 84

    def test_import_rejects_missing_scope(
        self, memory_db: Session, sample_xlsx_bytes: bytes
    ) -> None:
        service = BomPackagingTransportFeeImportService()
        with pytest.raises(BusinessException, match="采购基地"):
            service.import_excel(
                memory_db,
                file_content=sample_xlsx_bytes,
                filename="包装运输费用.xlsx",
                location="",
                year=YEAR,
                vehicle_model=VEHICLE_MODEL,
                current_user=SYSTEM_USER,
            )
        with pytest.raises(BusinessException, match="项目"):
            service.import_excel(
                memory_db,
                file_content=sample_xlsx_bytes,
                filename="包装运输费用.xlsx",
                location=LOCATION,
                year=YEAR,
                vehicle_model="",
                current_user=SYSTEM_USER,
            )
