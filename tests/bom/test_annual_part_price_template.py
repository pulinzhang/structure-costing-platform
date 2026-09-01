"""年度零件价导入模板：从采购对象「标准件/胶等」带出。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.exceptions.base import BusinessException
from app.models.bom.node import BomNode, BomSnapshot  # noqa: F401
from app.models.bom.procurement_object import (  # noqa: F401
    BomProcurementObject,
    BomProcurementObjectList,
)
from app.models.bom.procurement_object_generate_log import (  # noqa: F401
    BomProcurementObjectGenerateLog,
)
from app.parsers.bom.annual_part_price_parser import parse_annual_part_price_excel
from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.schemas.dto.bom_dto import BomNodeWrite, BomSnapshotWrite
from app.schemas.dto.bom_procurement_object_dto import BomProcurementObjectGenerateDTO
from app.services.bom.annual_part_price.import_service import BomAnnualPartPriceImportService
from app.services.bom.procurement_object.labels import SECTION_LABELS
from app.services.bom.procurement_object.service import BomProcurementObjectService


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _create_snapshot(
    db: Session,
    *,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> int:
    snapshot = BomSnapshotRepository().create(
        db,
        BomSnapshotWrite(
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            source_filename=f"{vehicle_model}.xlsx",
            created_by="tester",
            updated_by="tester",
        ),
    )
    return snapshot.id


def _add_stamping_tree(db: Session, *, snapshot_id: int) -> None:
    node_repo = BomNodeRepository()
    l0 = node_repo.create(
        db,
        BomNodeWrite(
            snapshot_id=snapshot_id,
            level=0,
            part_number="L0-STAMP",
            node_role="supply",
            created_by="tester",
            updated_by="tester",
            is_supply_unit=True,
            excel_filename="t.xlsx",
            excel_row=8,
        ),
    )
    node_repo.create(
        db,
        BomNodeWrite(
            snapshot_id=snapshot_id,
            parent_id=l0.id,
            level=1,
            part_number="L1-STAMP",
            node_role="make",
            created_by="tester",
            updated_by="tester",
            part_name="加强板",
            thickness_mm=Decimal("0.8000"),
            thickness_text="T=0.8",
            excel_filename="t.xlsx",
            excel_row=9,
        ),
    )


def _add_other_leaf(
    db: Session,
    *,
    snapshot_id: int,
    l0_part_number: str,
    part_number: str,
    part_name: str,
    excel_row: int,
) -> None:
    node_repo = BomNodeRepository()
    l0 = node_repo.create(
        db,
        BomNodeWrite(
            snapshot_id=snapshot_id,
            level=0,
            part_number=l0_part_number,
            node_role="supply",
            created_by="tester",
            updated_by="tester",
            is_supply_unit=True,
            excel_filename="t.xlsx",
            excel_row=excel_row,
        ),
    )
    node_repo.create(
        db,
        BomNodeWrite(
            snapshot_id=snapshot_id,
            parent_id=l0.id,
            level=1,
            part_number=part_number,
            part_name=part_name,
            node_role="buy",
            created_by="tester",
            updated_by="tester",
            qty_unit="pcs",
            excel_filename="t.xlsx",
            excel_row=excel_row + 1,
        ),
    )


def test_template_rejected_without_procurement_list(db: Session) -> None:
    with pytest.raises(BusinessException, match="请先生成该基地的采购对象清单"):
        BomAnnualPartPriceImportService().build_template(db, location="芜湖", year=2026)


def test_template_rejected_without_other_leaf(db: Session) -> None:
    snapshot_id = _create_snapshot(db, location="芜湖", vehicle_model="T13J", bom_version="V3")
    _add_stamping_tree(db, snapshot_id=snapshot_id)
    db.commit()
    BomProcurementObjectService().generate(
        db,
        BomProcurementObjectGenerateDTO(location="芜湖", vehicle_model="T13J", bom_version="V3"),
        current_user=SYSTEM_USER,
    )
    with pytest.raises(BusinessException, match="没有标准件/胶等"):
        BomAnnualPartPriceImportService().build_template(db, location="芜湖", year=2026)


def test_template_unions_other_leaf_and_dedupes(db: Session) -> None:
    first_id = _create_snapshot(db, location="芜湖", vehicle_model="T13J", bom_version="V3")
    _add_other_leaf(
        db,
        snapshot_id=first_id,
        l0_part_number="L0-A",
        part_number="QR36410",
        part_name="焊接方螺母",
        excel_row=8,
    )
    second_id = _create_snapshot(db, location="芜湖", vehicle_model="T28", bom_version="V1")
    _add_other_leaf(
        db,
        snapshot_id=second_id,
        l0_part_number="L0-B",
        part_number="QR36410",
        part_name="焊接方螺母-重复",
        excel_row=20,
    )
    _add_other_leaf(
        db,
        snapshot_id=second_id,
        l0_part_number="L0-C",
        part_number="M14-4102311",
        part_name="结构胶",
        excel_row=30,
    )
    db.commit()

    service = BomProcurementObjectService()
    service.generate(
        db,
        BomProcurementObjectGenerateDTO(location="芜湖", vehicle_model="T13J", bom_version="V3"),
        current_user=SYSTEM_USER,
    )
    service.generate(
        db,
        BomProcurementObjectGenerateDTO(location="芜湖", vehicle_model="T28", bom_version="V1"),
        current_user=SYSTEM_USER,
    )

    content, filename = BomAnnualPartPriceImportService().build_template(
        db, location="芜湖", year=2026
    )
    assert filename == "年度零件价导入模板_芜湖_2026.xlsx"

    workbook = load_workbook(BytesIO(content), data_only=True)
    sheet = workbook.active
    numbers = [str(row[0]) for row in sheet.iter_rows(min_row=2, values_only=True) if row[0]]
    assert numbers == ["QR36410", "M14-4102311"]
    assert sheet.cell(2, 2).value == "焊接方螺母"
    assert sheet.cell(2, 5).value == SECTION_LABELS["other_leaf"]
    assert sheet.cell(2, 4).value == Decimal("0.0000") or sheet.cell(2, 4).value == 0

    parsed = parse_annual_part_price_excel(content)
    assert parsed.errors == []
    assert [row.part_number for row in parsed.rows] == ["QR36410", "M14-4102311"]
    assert parsed.rows[0].supply_type == SECTION_LABELS["other_leaf"]
    assert parsed.rows[0].unit_price == Decimal("0.0000")
