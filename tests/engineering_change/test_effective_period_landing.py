"""BOM / 工艺 / 布点有效期落地：对照设计 §9。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.period import SOP_NEW_NUMBER_REJECT, require_export_as_of
from app.database import Base
from app.exceptions.base import BusinessException
from app.models.bom.node import BomNode, BomSnapshot
from app.models.masterdata.location import Location, LocationAlias
from app.models.masterdata.steel_grade_category import SteelGradeCategory
from app.models.masterdata.supplier import Supplier, SupplierAlias
from app.models.masterdata.vehicle_model import VehicleModel
from app.models.stamping.die import StampingDiePart, StampingDieProcess
from app.models.stamping.part import StampingPart
from app.parsers.bom.models import BomParsedMeta, BomParsedNode, BomParseResult
from app.parsers.stamping.die.types import ParsedDiePart, ParsedDieProcess
from app.parsers.stamping.models.part import Part
from app.repositories.stamping.stamping_die_repository import (
    StampingDiePartRepository,
    StampingDieProcessRepository,
)
from app.repositories.stamping.stamping_part_repository import StampingPartRepository
from app.schemas.dto.period_dto import EffectivePeriodUpdateDTO
from app.schemas.dto.stamping_die_fee_dto import StampingDieFeeCalcDTO
from app.schemas.dto.stamping_upload_dto import FileInfo
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom_service import BomService
from app.services.bom.upload.orchestrator import BomUploadOrchestrator
from app.services.bom.upload.orchestrator.types import BomUploadExecuteArgs
from app.services.bom.upload.persist.nodes import align_existing_trees
from app.services.stamping.die.die_number_assigner import assign_die_numbers
from app.services.stamping.die.export_service import StampingDieExportService
from app.services.stamping.die_fee.calc.orchestrator.prep import prepare_calc_run
from app.services.stamping.die_fee.calc.orchestrator.progress import ProgressNotifier
from app.services.stamping.part_export.helpers import PartExportStyle
from app.services.stamping.part_export.process_confirm import ProcessConfirmExport
from app.services.stamping.stamping_part_export_service import StampingPartExportService
from app.services.stamping.upload.persist.parts import save_parts

LOCATION = "青岛"
VEHICLE_MODEL = "T13J"
BOM_VERSION = "D/09"
SUPPLIER = "烟台海众汽车零部件有限公司"
VERSION = "V1"


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
        tables=[
            Location.__table__,
            LocationAlias.__table__,
            VehicleModel.__table__,
            Supplier.__table__,
            SupplierAlias.__table__,
            SteelGradeCategory.__table__,
            BomSnapshot.__table__,
            BomNode.__table__,
            StampingPart.__table__,
            StampingDiePart.__table__,
            StampingDieProcess.__table__,
        ],
    )
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    session.add(
        Location(
            location=LOCATION,
            is_enabled=True,
            sort_order=1,
            created_by="system",
            updated_by="system",
        )
    )
    session.add(
        VehicleModel(
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            effective_year=2024,
            effective_month=7,
            expiry_year=2028,
            expiry_month=12,
            created_by="system",
            updated_by="system",
        )
    )
    session.add(
        VehicleModel(
            location=LOCATION,
            vehicle_model="T99",
            effective_year=2023,
            effective_month=1,
            created_by="system",
            updated_by="system",
        )
    )
    session.add(
        Supplier(
            full_name=SUPPLIER,
            abbreviation="海众",
            erp_code="HZ001",
            is_enabled=True,
            sort_order=1,
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


def _user() -> UserVO:
    return UserVO(id=1, username="tester", real_name="测试员")


def _snapshot(db: Session, *, bom_version: str = BOM_VERSION) -> BomSnapshot:
    row = BomSnapshot(
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=bom_version,
        stage="initial",
        status="active",
        source_filename="sop.xlsx",
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _node(
    db: Session,
    snapshot: BomSnapshot,
    *,
    level: int,
    part_number: str,
    parent_id: int | None = None,
    seq_no: int | None = None,
    part_name: str | None = None,
    effective_year: int = 2024,
    effective_month: int = 7,
    expiry_year: int | None = 2028,
    expiry_month: int | None = 12,
) -> BomNode:
    row = BomNode(
        snapshot_id=snapshot.id,
        parent_id=parent_id,
        level=level,
        seq_no=seq_no,
        part_number=part_number,
        part_name=part_name,
        node_role="supply" if level == 0 else "make",
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        bom_version=snapshot.bom_version,
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _file_info() -> FileInfo:
    return FileInfo(
        file_path="x.xlsx",
        new_filename="x.xlsx",
        safe_location=LOCATION,
        safe_vehicle=VEHICLE_MODEL,
        safe_version=VERSION,
        upload_subdir="x",
    )


def _l0_parsed(part_number: str, *, part_name: str | None = None) -> BomParsedNode:
    return BomParsedNode(
        level=0,
        parent_index=None,
        sort_no=1,
        seq_no=1,
        part_number=part_number,
        part_name=part_name,
        node_role="supply",
    )


def _stub_bom_upload(
    monkeypatch: pytest.MonkeyPatch,
    *,
    bom_version: str,
    nodes: list[BomParsedNode],
) -> None:
    result = BomParseResult(
        meta=BomParsedMeta(vehicle_model=VEHICLE_MODEL, bom_version=bom_version),
        nodes=nodes,
        sheet_name="Sheet1",
    )
    monkeypatch.setattr(
        "app.services.bom.upload.orchestrator.prep.parse_bom_excel",
        lambda *_args, **_kwargs: result,
    )
    monkeypatch.setattr(
        "app.services.bom.upload.gates.validate.validate_internal_number_uniqueness",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.bom.upload.gates.validate.validate_subassembly_consistency",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.services.bom.upload.orchestrator.pipeline.save_excel_file",
        lambda *_args, **_kwargs: "bom/x.xlsx",
    )
    monkeypatch.setattr(
        "app.services.bom.upload.orchestrator.pipeline.save_node_sketches",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        "app.services.bom.upload.persist.nodes.register_existing",
        lambda *_args, **_kwargs: None,
    )


def test_require_export_as_of_missing_month() -> None:
    with pytest.raises(BusinessException) as caught:
        require_export_as_of(2026, None)
    assert caught.value.code == 422


def test_process_confirm_export_requires_year_month(memory_db: Session) -> None:
    exporter = ProcessConfirmExport(StampingPartRepository(), PartExportStyle())
    with pytest.raises(BusinessException) as caught:
        exporter.export(
            memory_db,
            location=LOCATION,
            current_user=_user(),
        )
    assert caught.value.code == 422


def test_process_confirm_export_rejects_empty(memory_db: Session) -> None:
    exporter = ProcessConfirmExport(StampingPartRepository(), PartExportStyle())
    with pytest.raises(BusinessException, match="没有零件"):
        exporter.export(
            memory_db,
            location=LOCATION,
            year=2026,
            month=9,
            current_user=_user(),
        )


def test_steel_purchase_export_rejects_empty(memory_db: Session) -> None:
    with pytest.raises(BusinessException, match="没有零件"):
        StampingPartExportService().export_steel_purchase(
            memory_db,
            location=LOCATION,
            current_user=_user(),
        )


def test_die_export_requires_year_month(memory_db: Session) -> None:
    with pytest.raises(BusinessException) as caught:
        StampingDieExportService().export_workbook(
            memory_db,
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            current_user=_user(),
        )
    assert caught.value.code == 422


def test_first_sop_copies_project_period_not_wall_clock(memory_db: Session) -> None:
    save_parts(
        memory_db,
        StampingPartRepository(),
        [Part(seq_no=1, part_number="P001", part_name="内板")],
        VEHICLE_MODEL,
        VERSION,
        _file_info(),
        {},
        SUPPLIER,
        "sop.xlsx",
        current_user=_user(),
    )
    memory_db.commit()
    row = memory_db.query(StampingPart).one()
    assert row.effective_year == 2024
    assert row.effective_month == 7
    assert row.expiry_year == 2028
    assert row.expiry_month == 12


def test_first_sop_empty_project_expiry_stays_empty(memory_db: Session) -> None:
    save_parts(
        memory_db,
        StampingPartRepository(),
        [Part(seq_no=1, part_number="P099", part_name="开口项目")],
        "T99",
        VERSION,
        _file_info(),
        {},
        SUPPLIER,
        "sop.xlsx",
        current_user=_user(),
    )
    memory_db.commit()
    row = memory_db.query(StampingPart).one()
    assert row.vehicle_model == "T99"
    assert row.effective_year == 2023
    assert row.effective_month == 1
    assert row.expiry_year is None
    assert row.expiry_month is None


def test_reimport_keeps_missing_number_and_patched_period(memory_db: Session) -> None:
    repo = StampingPartRepository()
    save_parts(
        memory_db,
        repo,
        [
            Part(seq_no=1, part_number="P001", part_name="一件"),
            Part(seq_no=2, part_number="P002", part_name="二件"),
        ],
        VEHICLE_MODEL,
        VERSION,
        _file_info(),
        {},
        SUPPLIER,
        "sop.xlsx",
        current_user=_user(),
    )
    memory_db.commit()
    first = repo.get_by_unique_key(
        memory_db,
        location=LOCATION,
        stamping_supplier=SUPPLIER,
        vehicle_model=VEHICLE_MODEL,
        part_number="P001",
    )
    assert first is not None
    first.effective_year = 2025
    first.effective_month = 1
    first.seq_no = 9
    memory_db.commit()

    save_parts(
        memory_db,
        repo,
        [Part(seq_no=3, part_number="P001", part_name="一件改名")],
        VEHICLE_MODEL,
        "V9",
        _file_info(),
        {},
        SUPPLIER,
        "again.xlsx",
        current_user=_user(),
    )
    memory_db.commit()
    numbers = {row.part_number for row in memory_db.query(StampingPart).all()}
    assert numbers == {"P001", "P002"}
    updated = repo.get_by_unique_key(
        memory_db,
        location=LOCATION,
        stamping_supplier=SUPPLIER,
        vehicle_model=VEHICLE_MODEL,
        part_number="P001",
    )
    assert updated is not None
    assert updated.part_name == "一件改名"
    assert updated.effective_year == 2025
    assert updated.effective_month == 1
    assert updated.seq_no == 9
    assert updated.version == VERSION


def test_existing_sop_rejects_new_number(memory_db: Session) -> None:
    repo = StampingPartRepository()
    save_parts(
        memory_db,
        repo,
        [Part(seq_no=1, part_number="P001")],
        VEHICLE_MODEL,
        VERSION,
        _file_info(),
        {},
        SUPPLIER,
        "sop.xlsx",
        current_user=_user(),
    )
    memory_db.commit()
    with pytest.raises(BusinessException, match=SOP_NEW_NUMBER_REJECT):
        save_parts(
            memory_db,
            repo,
            [Part(seq_no=1, part_number="P099")],
            VEHICLE_MODEL,
            VERSION,
            _file_info(),
            {},
            SUPPLIER,
            "new.xlsx",
            current_user=_user(),
        )


def test_bom_first_import_copies_project_period(
    memory_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_bom_upload(
        monkeypatch,
        bom_version=BOM_VERSION,
        nodes=[_l0_parsed("L0001AA", part_name="总成")],
    )
    BomUploadOrchestrator().execute(
        memory_db,
        BomUploadExecuteArgs(
            file_content=b"fake-xlsx",
            filename="sop.xlsx",
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
        ),
        _user(),
    )
    row = memory_db.query(BomNode).one()
    assert row.effective_year == 2024
    assert row.effective_month == 7
    assert row.expiry_year == 2028
    assert row.expiry_month == 12
    assert row.location == LOCATION
    assert row.vehicle_model == VEHICLE_MODEL
    assert row.bom_version == BOM_VERSION


def test_existing_sop_rejects_new_bom_version(
    memory_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _snapshot(memory_db)
    _stub_bom_upload(
        monkeypatch,
        bom_version="D/10",
        nodes=[_l0_parsed("L0001AA")],
    )
    with pytest.raises(BusinessException, match=SOP_NEW_NUMBER_REJECT):
        BomUploadOrchestrator().execute(
            memory_db,
            BomUploadExecuteArgs(
                file_content=b"fake-xlsx",
                filename="next.xlsx",
                location=LOCATION,
                vehicle_model=VEHICLE_MODEL,
            ),
            _user(),
        )


def test_bom_align_keeps_missing_l0_and_patched_period(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    kept = _node(memory_db, snapshot, level=0, part_number="KEEPAA", seq_no=1)
    patched = _node(
        memory_db,
        snapshot,
        level=0,
        part_number="PATCHAA",
        seq_no=2,
        part_name="旧名",
        effective_year=2025,
        effective_month=1,
        expiry_year=None,
        expiry_month=None,
    )
    ec_tree = _node(
        memory_db,
        snapshot,
        level=0,
        part_number="ECTREEAB",
        seq_no=3,
        part_name="合册树",
        effective_year=2025,
        effective_month=7,
        expiry_year=None,
        expiry_month=None,
    )
    align_existing_trees(
        memory_db,
        snapshot_id=snapshot.id,
        existing_l0={
            kept.part_number: kept,
            patched.part_number: patched,
            ec_tree.part_number: ec_tree,
        },
        parsed_nodes=[
            _l0_parsed("PATCHAA", part_name="新名"),
            _l0_parsed("ECTREEAB", part_name="不应被重建"),
        ],
        saved_images={},
        original_name="again.xlsx",
        sheet_name="Sheet1",
        updated_by="tester",
        sop_year=2025,
        sop_month=1,
    )
    memory_db.commit()
    numbers = {row.part_number for row in memory_db.query(BomNode).filter(BomNode.level == 0).all()}
    assert numbers == {"KEEPAA", "PATCHAA", "ECTREEAB"}
    memory_db.refresh(patched)
    memory_db.refresh(ec_tree)
    assert patched.part_name == "新名"
    assert patched.effective_year == 2025
    assert patched.effective_month == 1
    assert patched.expiry_year is None
    assert patched.seq_no == 2
    assert ec_tree.part_name == "合册树"


def test_l0_patch_cascades_l1_reject_and_seq_overlap(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    l0 = _node(memory_db, snapshot, level=0, part_number="L0001AA", seq_no=1)
    child = _node(memory_db, snapshot, level=1, part_number="L1001AA", parent_id=l0.id)
    other = _node(
        memory_db,
        snapshot,
        level=0,
        part_number="L0002AA",
        seq_no=1,
        effective_year=2024,
        effective_month=7,
        expiry_year=2025,
        expiry_month=12,
    )
    service = BomService()
    dto = EffectivePeriodUpdateDTO(
        effective_year=2026,
        effective_month=1,
        expiry_year=2026,
        expiry_month=6,
    )
    service.patch_node_period(memory_db, l0.id, dto, current_user=_user())
    memory_db.refresh(child)
    assert child.effective_year == 2026
    assert child.effective_month == 1
    assert child.expiry_month == 6

    with pytest.raises(BusinessException, match="只能改总成"):
        service.patch_node_period(memory_db, child.id, dto, current_user=_user())

    with pytest.raises(BusinessException, match="同一序号"):
        service.patch_node_period(
            memory_db,
            other.id,
            EffectivePeriodUpdateDTO(
                effective_year=2026,
                effective_month=3,
                expiry_year=2026,
                expiry_month=8,
            ),
            current_user=_user(),
        )


def test_tree_as_of_hides_expired_l0(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    _node(
        memory_db,
        snapshot,
        level=0,
        part_number="LIVEAA",
        seq_no=1,
        effective_year=2024,
        effective_month=7,
        expiry_year=None,
        expiry_month=None,
    )
    _node(
        memory_db,
        snapshot,
        level=0,
        part_number="OLDAA",
        seq_no=2,
        effective_year=2024,
        effective_month=7,
        expiry_year=2025,
        expiry_month=12,
    )
    tree = BomService().list_nodes_tree(memory_db, snapshot.id, year=2026, month=9)
    numbers = {node.part_number for node in tree}
    assert numbers == {"LIVEAA"}
    full = BomService().list_nodes_tree(
        memory_db, snapshot.id, year=2026, month=9, include_expired=True
    )
    assert {node.part_number for node in full} == {"LIVEAA", "OLDAA"}


def test_stamping_unique_excludes_version(memory_db: Session) -> None:
    memory_db.add(
        StampingPart(
            location=LOCATION,
            stamping_supplier=SUPPLIER,
            vehicle_model=VEHICLE_MODEL,
            version="V1",
            part_number="P001",
            excel_filename="a.xlsx",
            effective_year=2024,
            effective_month=7,
            created_by="system",
            updated_by="system",
        )
    )
    memory_db.commit()
    memory_db.add(
        StampingPart(
            location=LOCATION,
            stamping_supplier=SUPPLIER,
            vehicle_model=VEHICLE_MODEL,
            version="V2",
            part_number="P001",
            excel_filename="b.xlsx",
            effective_year=2025,
            effective_month=1,
            created_by="system",
            updated_by="system",
        )
    )
    with pytest.raises(IntegrityError):
        memory_db.commit()
    memory_db.rollback()


def test_l0_partial_unique_allows_l1_same_number(memory_db: Session) -> None:
    snapshot = _snapshot(memory_db)
    first = _node(memory_db, snapshot, level=0, part_number="ROOTAA", seq_no=1)
    second = _node(memory_db, snapshot, level=0, part_number="ROOTBB", seq_no=2)
    _node(memory_db, snapshot, level=1, part_number="SHAREAA", parent_id=first.id)
    _node(memory_db, snapshot, level=1, part_number="SHAREAA", parent_id=second.id)
    assert memory_db.query(BomNode).filter(BomNode.part_number == "SHAREAA").count() == 2
    memory_db.add(
        BomNode(
            snapshot_id=snapshot.id,
            level=0,
            part_number="ROOTAA",
            node_role="supply",
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            bom_version=BOM_VERSION,
            effective_year=2026,
            effective_month=1,
            created_by="system",
            updated_by="system",
        )
    )
    with pytest.raises(IntegrityError):
        memory_db.commit()
    memory_db.rollback()


def test_expired_die_number_still_occupies_serial(memory_db: Session) -> None:
    part = StampingDiePart(
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        part_number="D001",
        excel_filename="die.xlsx",
        effective_year=2024,
        effective_month=7,
        expiry_year=2025,
        expiry_month=12,
        created_by="system",
        updated_by="system",
    )
    memory_db.add(part)
    memory_db.commit()
    memory_db.refresh(part)
    memory_db.add(
        StampingDieProcess(
            die_part_id=part.id,
            process_seq="OP10",
            process_order=1,
            die_number="DP-40-T13J-001",
            created_by="system",
            updated_by="system",
        )
    )
    memory_db.commit()
    occupied = StampingDieProcessRepository().list_die_numbers_for_scope(
        memory_db, location=LOCATION, vehicle_model=VEHICLE_MODEL
    )
    assert "DP-40-T13J-001" in occupied
    assigned = assign_die_numbers(
        vehicle_model=VEHICLE_MODEL,
        existing_numbers=occupied,
        parts=[
            ParsedDiePart(
                seq_no=1,
                part_number="D002",
                part_name="新件",
                material=None,
                thickness=None,
                part_weight=None,
                sheet_length=None,
                sheet_width=None,
                sheet_shape=None,
                parts_per_sheet=None,
                material_consumption=None,
                material_utilization=None,
                estimated_weight_subtotal_t=None,
                die_type=None,
                die_method=None,
                production_mode=None,
                needs_end_effector=None,
                part_grade=None,
                remark=None,
                excel_sheet_name=None,
                excel_row=2,
                excel_part_col=1,
                processes=[
                    ParsedDieProcess(
                        process_seq="OP10",
                        process_code="OP",
                        die_sets=1,
                        die_number=None,
                        die_length=Decimal("100"),
                        die_width=Decimal("80"),
                        die_height=Decimal("50"),
                        hollow_factor=None,
                        estimated_weight_t=Decimal("1"),
                        tonnage=800,
                        excel_row=2,
                    )
                ],
            )
        ],
    )
    assert assigned.by_key[("D002", "OP10")] == "DP-40-T13J-002"


def test_die_unique_is_location_vehicle_part_number(memory_db: Session) -> None:
    memory_db.add(
        StampingDiePart(
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            part_number="D001",
            excel_filename="a.xlsx",
            effective_year=2024,
            effective_month=7,
            created_by="system",
            updated_by="system",
        )
    )
    memory_db.commit()
    memory_db.add(
        StampingDiePart(
            location=LOCATION,
            vehicle_model=VEHICLE_MODEL,
            part_number="D001",
            excel_filename="b.xlsx",
            effective_year=2026,
            effective_month=1,
            created_by="system",
            updated_by="system",
        )
    )
    with pytest.raises(IntegrityError):
        memory_db.commit()
    memory_db.rollback()


def _die_part(
    db: Session,
    *,
    part_number: str,
    vehicle_model: str = VEHICLE_MODEL,
    effective_year: int = 2024,
    effective_month: int = 7,
    expiry_year: int | None = 2028,
    expiry_month: int | None = 12,
) -> StampingDiePart:
    row = StampingDiePart(
        location=LOCATION,
        vehicle_model=vehicle_model,
        part_number=part_number,
        excel_filename="die.xlsx",
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_die_fee_year_overlap_uses_part_period_not_project(memory_db: Session) -> None:
    repo = StampingDiePartRepository()
    _die_part(
        memory_db,
        part_number="DEAD",
        expiry_year=2025,
        expiry_month=12,
    )
    assert repo.list_vehicle_models(memory_db, location=LOCATION, overlap_year=2026) == []
    _die_part(
        memory_db,
        part_number="AUG",
        effective_year=2026,
        effective_month=8,
        expiry_year=None,
        expiry_month=None,
    )
    _die_part(
        memory_db,
        part_number="LIVE",
        expiry_year=None,
        expiry_month=None,
    )
    overlapping = repo.list_with_processes(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        overlap_year=2026,
    )
    assert {row.part_number for row in overlapping} == {"AUG", "LIVE"}
    full = repo.list_with_processes(memory_db, location=LOCATION, vehicle_model=VEHICLE_MODEL)
    assert {row.part_number for row in full} == {"DEAD", "AUG", "LIVE"}
    assert repo.list_vehicle_models(memory_db, location=LOCATION, overlap_year=2026) == [
        VEHICLE_MODEL
    ]

    with pytest.raises(BusinessException, match="2026 年没有有效期内的模具布点"):
        prepare_calc_run(
            memory_db,
            SimpleNamespace(die_repo=repo),
            StampingDieFeeCalcDTO(year=2026, location=LOCATION, vehicle_model="T99"),
            ProgressNotifier(),
        )


def test_die_fee_year_overlap_keeps_expired_project_with_live_die(
    memory_db: Session,
) -> None:
    """布点列表年交集仍可见停产项目下的活件（查询，不是计算入口）。"""
    memory_db.add(
        VehicleModel(
            location=LOCATION,
            vehicle_model="T88",
            effective_year=2023,
            effective_month=1,
            expiry_year=2025,
            expiry_month=12,
            created_by="system",
            updated_by="system",
        )
    )
    memory_db.commit()
    _die_part(
        memory_db,
        part_number="KEEP",
        vehicle_model="T88",
        effective_year=2023,
        effective_month=1,
        expiry_year=None,
        expiry_month=None,
    )
    repo = StampingDiePartRepository()
    rows = repo.list_with_processes(
        memory_db, location=LOCATION, vehicle_model="T88", overlap_year=2026
    )
    assert [row.part_number for row in rows] == ["KEEP"]
    assert repo.list_vehicle_models(memory_db, location=LOCATION, overlap_year=2026) == ["T88"]
    assert repo.list_vehicle_models(memory_db, location=LOCATION, overlap_year=2022) == []


def _stamping_part(
    db: Session,
    *,
    part_number: str,
    vehicle_model: str = VEHICLE_MODEL,
    version: str = VERSION,
    effective_year: int = 2024,
    effective_month: int = 7,
    expiry_year: int | None = 2028,
    expiry_month: int | None = 12,
) -> StampingPart:
    row = StampingPart(
        location=LOCATION,
        stamping_supplier=SUPPLIER,
        vehicle_model=vehicle_model,
        version=version,
        part_number=part_number,
        excel_filename="part.xlsx",
        effective_year=effective_year,
        effective_month=effective_month,
        expiry_year=expiry_year,
        expiry_month=expiry_month,
        created_by="system",
        updated_by="system",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_part_cost_as_of_uses_part_period_not_project(memory_db: Session) -> None:
    repo = StampingPartRepository()
    _stamping_part(
        memory_db,
        part_number="DEAD",
        expiry_year=2026,
        expiry_month=6,
    )
    _stamping_part(
        memory_db,
        part_number="AUG",
        effective_year=2026,
        effective_month=8,
        expiry_year=None,
        expiry_month=None,
    )
    _stamping_part(
        memory_db,
        part_number="LIVE",
        expiry_year=None,
        expiry_month=None,
    )
    july = repo.list_by_location_and_vehicle(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        as_of_year=2026,
        as_of_month=7,
    )
    assert {row.part_number for row in july} == {"LIVE"}
    august = repo.list_by_location_and_vehicle(
        memory_db,
        location=LOCATION,
        vehicle_model=VEHICLE_MODEL,
        as_of_year=2026,
        as_of_month=8,
    )
    assert {row.part_number for row in august} == {"AUG", "LIVE"}
    full = repo.list_by_location_and_vehicle(
        memory_db, location=LOCATION, vehicle_model=VEHICLE_MODEL
    )
    assert {row.part_number for row in full} == {"DEAD", "AUG", "LIVE"}


def test_part_cost_as_of_keeps_expired_project_with_live_part(memory_db: Session) -> None:
    """列表 as_of 仍可见停产项目下的活件（查询，不是计算入口）。"""
    memory_db.add(
        VehicleModel(
            location=LOCATION,
            vehicle_model="T88",
            effective_year=2023,
            effective_month=1,
            expiry_year=2025,
            expiry_month=12,
            created_by="system",
            updated_by="system",
        )
    )
    memory_db.commit()
    _stamping_part(
        memory_db,
        part_number="KEEP",
        vehicle_model="T88",
        effective_year=2023,
        effective_month=1,
        expiry_year=None,
        expiry_month=None,
    )
    repo = StampingPartRepository()
    rows = repo.list_by_location_and_vehicle(
        memory_db,
        location=LOCATION,
        vehicle_model="T88",
        as_of_year=2026,
        as_of_month=7,
    )
    assert [row.part_number for row in rows] == ["KEEP"]
