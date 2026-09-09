"""采购对象清单 Service 测试（内存 SQLite）。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.exceptions.base import BusinessException
from app.models.bom.node import BomNode, BomSnapshot
from app.models.bom.procurement_object import (  # noqa: F401
    BomProcurementObject,
    BomProcurementObjectList,
)
from app.models.bom.procurement_object_generate_log import (  # noqa: F401
    BomProcurementObjectGenerateLog,
)
from app.models.masterdata.location import Location, LocationAlias  # noqa: F401
from app.models.masterdata.supplier import Supplier, SupplierAlias  # noqa: F401
from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.repositories.masterdata.location.location_repository import LocationRepository
from app.schemas.dto.bom_dto import BomNodeWrite, BomSnapshotWrite
from app.schemas.dto.bom_procurement_object_dto import (
    BomProcurementObjectBatchApproveDTO,
    BomProcurementObjectBatchDeleteDTO,
    BomProcurementObjectBatchReverseAuditDTO,
    BomProcurementObjectConfirmDTO,
    BomProcurementObjectGenerateDTO,
    BomProcurementObjectGenerateLogQuery,
    BomProcurementObjectQuery,
)
from app.schemas.dto.location_dto import LocationAliasInsert, LocationInsert
from app.services.bom.procurement_object.export import BomProcurementObjectExportService
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
    repo = LocationRepository()
    repo.create(
        session,
        LocationInsert(
            location="芜湖",
            is_enabled=True,
            sort_order=1,
            created_by="system",
            updated_by="system",
        ),
    )
    repo.create_alias(session, LocationAliasInsert(alias="芜湖基地", location="芜湖"))
    session.flush()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_tree(db: Session) -> None:
    snapshot = BomSnapshotRepository().create(
        db,
        BomSnapshotWrite(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="V3",
            source_filename="t13j.xlsx",
            created_by="tester",
            updated_by="tester",
        ),
    )
    node_repo = BomNodeRepository()
    l0 = node_repo.create(
        db,
        BomNodeWrite(
            snapshot_id=snapshot.id,
            level=0,
            part_number="L0-A",
            node_role="supply",
            created_by="tester",
            updated_by="tester",
            is_supply_unit=True,
            excel_filename="t13j.xlsx",
            excel_row=8,
            weld_info="焊点:4",
        ),
    )
    node_repo.create(
        db,
        BomNodeWrite(
            snapshot_id=snapshot.id,
            parent_id=l0.id,
            level=1,
            part_number="L1-STAMP",
            node_role="make",
            created_by="tester",
            updated_by="tester",
            part_name="加强板",
            internal_number="ACA674001",
            thickness_mm=Decimal("0.8000"),
            thickness_text="T=0.8",
            excel_filename="t13j.xlsx",
            excel_row=9,
        ),
    )
    db.commit()


def _scope() -> BomProcurementObjectGenerateDTO:
    return BomProcurementObjectGenerateDTO(
        location="芜湖",
        vehicle_model="T13J",
        bom_version="V3",
    )


def test_generate_and_regenerate_keeps_confirm(db: Session) -> None:
    _seed_tree(db)
    service = BomProcurementObjectService()
    first = service.generate(db, _scope(), current_user=SYSTEM_USER)
    assert first.object_count == 1
    items, total, _filters = service.paginate(
        db,
        BomProcurementObjectQuery(location="芜湖", vehicle_model="T13J", bom_version="V3", size=50),
    )
    assert total == 1
    assert items[0].internal_number == "ACA674001"
    confirmed = service.confirm(
        db,
        items[0].id,
        BomProcurementObjectConfirmDTO(confirm_status="outsourced", confirm_remark="外发"),
        current_user=SYSTEM_USER,
    )
    assert confirmed.confirm_status == "outsourced"
    second = service.generate(db, _scope(), current_user=SYSTEM_USER)
    assert second.object_count == 1
    items2, _, _ = service.paginate(
        db,
        BomProcurementObjectQuery(location="芜湖", vehicle_model="T13J", bom_version="V3", size=50),
    )
    assert items2[0].confirm_status == "outsourced"
    logs, log_total = service.list_generate_logs(db, BomProcurementObjectGenerateLogQuery(size=20))
    assert log_total == 2
    assert logs[0].status == "success"
    assert logs[0].object_count == 1
    assert "采购对象" in logs[0].detail_text
    assert "退化供货件亚类" in logs[0].detail_text
    assert "已按毛坯供货" not in logs[0].detail_text


def test_generate_blocked_when_approved(db: Session) -> None:
    _seed_tree(db)
    service = BomProcurementObjectService()
    service.generate(db, _scope(), current_user=SYSTEM_USER)
    service.batch_approve(
        db,
        BomProcurementObjectBatchApproveDTO(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="V3",
            audit_remark="通过",
        ),
        current_user=SYSTEM_USER,
    )
    with pytest.raises(BusinessException) as exc:
        service.generate(db, _scope(), current_user=SYSTEM_USER)
    assert exc.value.code == 409
    logs, log_total = service.list_generate_logs(db, BomProcurementObjectGenerateLogQuery(size=20))
    assert log_total == 2
    assert logs[0].status == "failed"
    assert "已审核" in logs[0].detail_text


def test_batch_approve_empty_remark_rejected_by_dto() -> None:
    with pytest.raises(ValidationError):
        BomProcurementObjectBatchApproveDTO(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="V3",
            audit_remark="",
        )


def test_delete_skips_approved(db: Session) -> None:
    _seed_tree(db)
    service = BomProcurementObjectService()
    service.generate(db, _scope(), current_user=SYSTEM_USER)
    service.batch_approve(
        db,
        BomProcurementObjectBatchApproveDTO(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="V3",
            audit_remark="通过",
        ),
        current_user=SYSTEM_USER,
    )
    result = service.batch_delete(
        db,
        BomProcurementObjectBatchDeleteDTO(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="V3",
        ),
        current_user=SYSTEM_USER,
    )
    assert result.deleted_count == 0
    assert result.skipped_approved_count == 1


def test_confirm_rejected_when_approved(db: Session) -> None:
    _seed_tree(db)
    service = BomProcurementObjectService()
    service.generate(db, _scope(), current_user=SYSTEM_USER)
    items, _, _ = service.paginate(
        db,
        BomProcurementObjectQuery(location="芜湖", vehicle_model="T13J", bom_version="V3", size=50),
    )
    service.batch_approve(
        db,
        BomProcurementObjectBatchApproveDTO(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="V3",
            audit_remark="通过",
        ),
        current_user=SYSTEM_USER,
    )
    with pytest.raises(BusinessException, match="已审核"):
        service.confirm(
            db,
            items[0].id,
            BomProcurementObjectConfirmDTO(confirm_status="in_house"),
            current_user=SYSTEM_USER,
        )


def test_batch_reverse_audit_required_remark() -> None:
    with pytest.raises(ValidationError):
        BomProcurementObjectBatchReverseAuditDTO(
            location="芜湖",
            vehicle_model="T13J",
            bom_version="V3",
            reverse_audit_remark="",
        )


def test_export_workbook_has_styled_sheets_without_cover(db: Session) -> None:
    _seed_tree(db)
    BomProcurementObjectService().generate(db, _scope(), current_user=SYSTEM_USER)
    content, filename = BomProcurementObjectExportService().export_excel(
        db,
        BomProcurementObjectQuery(location="芜湖", vehicle_model="T13J", bom_version="V3"),
        SYSTEM_USER,
    )
    assert filename.startswith("采购对象清单_芜湖_T13J_V3_")
    assert filename.endswith(".xlsx")
    workbook = load_workbook(BytesIO(content))
    assert workbook.sheetnames == ["采购对象", "标准件及胶等", "异常"]
    object_sheet = workbook["采购对象"]
    assert object_sheet["A1"].value == "采购对象清单 · 采购对象"
    assert object_sheet["A4"].value == "对着原件"
    assert object_sheet["A5"].value == "Excel行号"
    assert object_sheet["C5"].value == "零件号"
    assert object_sheet["D5"].value == "短码"
    assert object_sheet["E5"].value == "内部号"
    assert object_sheet["F5"].value == "零件名称"
    assert object_sheet["I5"].value == "对象种类"
    assert object_sheet["K5"].value == "供应商"
    assert object_sheet["M5"].value == "材料"
    assert object_sheet["M4"].value == "佐证"
    assert object_sheet.freeze_panes == "I6"
    assert object_sheet["A6"].value == 9
    assert object_sheet["C6"].value == "L1-STAMP"
    assert object_sheet["D6"].value is None
    assert object_sheet["E6"].value == "ACA674001"
    assert object_sheet["U6"].value == "芜湖"
    assert object_sheet["C6"].font.color.rgb in {"0037474F", "37474F"}
    assert object_sheet["D6"].font.color.rgb in {"001F4E79", "1F4E79"}
    assert object_sheet["E6"].font.color.rgb in {"00808080", "808080"}
    assert object_sheet["U6"].font.color.rgb in {"00455A64", "455A64"}
    assert object_sheet["A1"].fill.fgColor.rgb in {"001A237E", "1A237E"}
    workbook.close()


def test_export_merges_same_l0_assembly_cells(db: Session) -> None:
    _seed_tree(db)
    snapshot = db.query(BomSnapshot).filter(BomSnapshot.vehicle_model == "T13J").one()
    l0 = db.query(BomNode).filter(BomNode.part_number == "L0-A").one()
    BomNodeRepository().create(
        db,
        BomNodeWrite(
            snapshot_id=snapshot.id,
            parent_id=l0.id,
            level=1,
            part_number="L1-STAMP-2",
            node_role="make",
            created_by="tester",
            updated_by="tester",
            part_name="加强板2",
            internal_number="ACA674002",
            thickness_mm=Decimal("0.8000"),
            thickness_text="T=0.8",
            excel_filename="t13j.xlsx",
            excel_row=10,
        ),
    )
    db.commit()
    BomProcurementObjectService().generate(db, _scope(), current_user=SYSTEM_USER)
    content, _filename = BomProcurementObjectExportService().export_excel(
        db,
        BomProcurementObjectQuery(location="芜湖", vehicle_model="T13J", bom_version="V3"),
        SYSTEM_USER,
    )
    workbook = load_workbook(BytesIO(content))
    object_sheet = workbook["采购对象"]
    merged = {str(item) for item in object_sheet.merged_cells.ranges}
    assert "G6:G7" in merged
    assert "H6:H7" in merged
    assert object_sheet["G6"].value == "L0-A"
    workbook.close()
