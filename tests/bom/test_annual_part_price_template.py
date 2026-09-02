"""年度零件价导入模板：基地+项目外购叶子（other_leaf ∪ 非工艺库）。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.exceptions.base import BusinessException
from app.models.bom.node import BomNode, BomSnapshot  # noqa: F401
from app.models.stamping.part import StampingPart
from app.parsers.bom.annual_part_price_parser import parse_annual_part_price_excel
from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.schemas.dto.bom_dto import BomNodeWrite, BomSnapshotWrite
from app.services.bom.annual_part_price.import_service import BomAnnualPartPriceImportService
from app.services.bom.annual_part_price.template_source import (
    SUPPLY_TYPE_CARRYOVER,
    SUPPLY_TYPE_GLUE,
    SUPPLY_TYPE_STANDARD,
)


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


def _add_process_library_part(
    db: Session,
    *,
    location: str,
    vehicle_model: str,
    part_number: str,
) -> None:
    db.add(
        StampingPart(
            location=location,
            vehicle_model=vehicle_model,
            version="V1",
            part_number=part_number,
            part_name=part_number,
            excel_filename="process.xlsx",
        )
    )


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


def _add_subassembly_with_l2(
    db: Session,
    *,
    snapshot_id: int,
) -> None:
    """L1 分总成 + L2 板料 + L2 螺母。"""
    node_repo = BomNodeRepository()
    l0 = node_repo.create(
        db,
        BomNodeWrite(
            snapshot_id=snapshot_id,
            level=0,
            part_number="L0-HINGE",
            node_role="supply",
            created_by="tester",
            updated_by="tester",
            is_supply_unit=True,
            excel_filename="t.xlsx",
            excel_row=40,
        ),
    )
    l1 = node_repo.create(
        db,
        BomNodeWrite(
            snapshot_id=snapshot_id,
            parent_id=l0.id,
            level=1,
            part_number="551001137AA",
            part_name="左后门上铰链安装板总成",
            node_role="make",
            created_by="tester",
            updated_by="tester",
            excel_filename="t.xlsx",
            excel_row=41,
        ),
    )
    node_repo.create(
        db,
        BomNodeWrite(
            snapshot_id=snapshot_id,
            parent_id=l1.id,
            level=2,
            part_number="551001133AA",
            part_name="左后门上铰链安装板",
            node_role="make",
            created_by="tester",
            updated_by="tester",
            thickness_mm=Decimal("1.2000"),
            thickness_text="T=1.2",
            excel_filename="t.xlsx",
            excel_row=42,
        ),
    )
    node_repo.create(
        db,
        BomNodeWrite(
            snapshot_id=snapshot_id,
            parent_id=l1.id,
            level=2,
            part_number="QR36410",
            part_name="焊接方螺母",
            node_role="buy",
            created_by="tester",
            updated_by="tester",
            qty_unit="pcs",
            excel_filename="t.xlsx",
            excel_row=43,
        ),
    )


def _download_template(db: Session, *, vehicle_model: str = "T13J"):
    return BomAnnualPartPriceImportService().build_template(
        db, location="芜湖", vehicle_model=vehicle_model, year=2026
    )


def test_template_rejected_without_project(db: Session) -> None:
    with pytest.raises(BusinessException, match="请选择项目"):
        BomAnnualPartPriceImportService().build_template(
            db, location="芜湖", vehicle_model="  ", year=2026
        )


def test_template_rejected_without_bom(db: Session) -> None:
    with pytest.raises(BusinessException, match="请先上传该基地该项目的材料清单"):
        _download_template(db)


def test_template_rejected_when_all_leaves_in_process_library(db: Session) -> None:
    snapshot_id = _create_snapshot(db, location="芜湖", vehicle_model="T13J", bom_version="V3")
    _add_stamping_tree(db, snapshot_id=snapshot_id)
    _add_process_library_part(db, location="芜湖", vehicle_model="T13J", part_number="L1-STAMP")
    db.commit()
    with pytest.raises(BusinessException, match="没有需填年度价的外购叶子"):
        _download_template(db)


def test_template_unions_project_versions_and_dedupes(db: Session) -> None:
    first_id = _create_snapshot(db, location="芜湖", vehicle_model="T13J", bom_version="V3")
    _add_other_leaf(
        db,
        snapshot_id=first_id,
        l0_part_number="L0-A",
        part_number="QR36410",
        part_name="焊接方螺母",
        excel_row=8,
    )
    second_id = _create_snapshot(db, location="芜湖", vehicle_model="T13J", bom_version="V4")
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
    other_project = _create_snapshot(db, location="芜湖", vehicle_model="T28", bom_version="V1")
    _add_other_leaf(
        db,
        snapshot_id=other_project,
        l0_part_number="L0-D",
        part_number="T28-ONLY",
        part_name="他项目件",
        excel_row=50,
    )
    db.commit()

    content, filename = _download_template(db)
    assert filename == "年度零件价导入模板_芜湖_T13J_2026.xlsx"

    workbook = load_workbook(BytesIO(content), data_only=True)
    sheet = workbook.active
    numbers = [str(row[0]) for row in sheet.iter_rows(min_row=2, values_only=True) if row[0]]
    assert numbers == ["QR36410", "M14-4102311"]
    assert "T28-ONLY" not in numbers
    assert sheet.cell(2, 2).value == "焊接方螺母"
    assert sheet.cell(2, 5).value == SUPPLY_TYPE_STANDARD
    assert sheet.cell(3, 5).value == SUPPLY_TYPE_GLUE
    assert sheet.cell(2, 4).value == Decimal("0.0000") or sheet.cell(2, 4).value == 0

    parsed = parse_annual_part_price_excel(content)
    assert parsed.errors == []
    assert [row.part_number for row in parsed.rows] == ["QR36410", "M14-4102311"]
    assert parsed.rows[0].supply_type == SUPPLY_TYPE_STANDARD
    assert parsed.rows[1].supply_type == SUPPLY_TYPE_GLUE
    assert parsed.rows[0].unit_price == Decimal("0.0000")


def test_template_includes_l2_not_in_process_library(db: Session) -> None:
    snapshot_id = _create_snapshot(db, location="芜湖", vehicle_model="T13J", bom_version="D/09")
    _add_subassembly_with_l2(db, snapshot_id=snapshot_id)
    db.commit()

    content, _filename = _download_template(db)
    workbook = load_workbook(BytesIO(content), data_only=True)
    sheet = workbook.active
    numbers = [str(row[0]) for row in sheet.iter_rows(min_row=2, values_only=True) if row[0]]
    assert numbers == ["551001133AA", "QR36410"]
    assert "551001137AA" not in numbers
    by_number = {
        str(row[0]): str(row[4]) for row in sheet.iter_rows(min_row=2, values_only=True) if row[0]
    }
    assert by_number["551001133AA"] == SUPPLY_TYPE_CARRYOVER
    assert by_number["QR36410"] == SUPPLY_TYPE_STANDARD


def test_template_excludes_l2_that_is_in_process_library(db: Session) -> None:
    snapshot_id = _create_snapshot(db, location="芜湖", vehicle_model="T13J", bom_version="D/09")
    _add_subassembly_with_l2(db, snapshot_id=snapshot_id)
    _add_process_library_part(db, location="芜湖", vehicle_model="T13J", part_number="551001133AA")
    db.commit()

    content, _filename = _download_template(db)
    workbook = load_workbook(BytesIO(content), data_only=True)
    sheet = workbook.active
    numbers = [str(row[0]) for row in sheet.iter_rows(min_row=2, values_only=True) if row[0]]
    assert numbers == ["QR36410"]
    assert "551001133AA" not in numbers
    assert "551001137AA" not in numbers
