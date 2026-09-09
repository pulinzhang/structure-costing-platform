"""文件溯源 — 分类权限与 supersede 键。"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base
from app.models.file_trace.upload_file import UploadFile
from app.repositories.file_trace.upload_file_repository import UploadFileRepository
from app.schemas.vo.user_vo import UserVO
from app.services.file_trace.categories import FILE_CATEGORY_LABELS, resolve_allowed_categories
from app.services.file_trace.register import register_existing

_repo = UploadFileRepository()


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
    Base.metadata.create_all(bind=engine, tables=[UploadFile.__table__])
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _admin_user() -> UserVO:
    return UserVO(
        id=1,
        username="admin",
        real_name="Admin",
        is_admin=True,
        permissions=["*"],
    )


def _limited_user(*permissions: str) -> UserVO:
    return UserVO(
        id=2,
        username="bom_user",
        real_name="BOM",
        is_admin=False,
        permissions=list(permissions),
    )


def _write_excel(upload_dir: Path, relpath: str, content: bytes = b"excel") -> str:
    target = upload_dir / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
    return relpath.replace("\\", "/")


def test_resolve_allowed_categories_intersection() -> None:
    admin = _admin_user()
    assert len(resolve_allowed_categories(admin)) == len(FILE_CATEGORY_LABELS)

    bom_only = _limited_user("menu:file-trace", "op:file-trace:view", "op:bom-upload:view")
    assert resolve_allowed_categories(bom_only) == ["bom_material"]

    tonnage_only = _limited_user(
        "menu:file-trace",
        "op:file-trace:view",
        "op:stamping-tonnage:view",
    )
    assert resolve_allowed_categories(tonnage_only) == ["stamping_tonnage_price"]

    welding_only = _limited_user(
        "menu:file-trace",
        "op:file-trace:view",
        "op:bom-welding-unit-price:view",
    )
    assert resolve_allowed_categories(welding_only) == ["bom_welding_unit_price"]

    annual_only = _limited_user(
        "menu:file-trace",
        "op:file-trace:view",
        "op:bom-annual-part-price:view",
    )
    assert resolve_allowed_categories(annual_only) == ["bom_annual_part_price"]

    procurement_supplier_only = _limited_user(
        "menu:file-trace",
        "op:file-trace:view",
        "op:bom-procurement-object-supplier-upload:view",
    )
    assert resolve_allowed_categories(procurement_supplier_only) == [
        "bom_procurement_object_supplier"
    ]

    menu_only = _limited_user("menu:file-trace", "op:file-trace:view")
    assert resolve_allowed_categories(menu_only) == []


def test_register_tonnage_price_supersedes_same_scope(memory_db: Session, tmp_path: Path) -> None:
    upload_dir = settings.UPLOAD_DIR
    relpath_v1 = _write_excel(upload_dir, "stamping/tonnage-price/2026/qd/a.xlsx", b"v1")
    relpath_v2 = _write_excel(upload_dir, "stamping/tonnage-price/2026/qd/b.xlsx", b"v2")
    user = _admin_user()

    first = register_existing(
        memory_db,
        file_category="stamping_tonnage_price",
        stored_relpath=relpath_v1,
        original_filename="a.xlsx",
        current_user=user,
        location="qd",
        year=2026,
    )
    memory_db.commit()

    second = register_existing(
        memory_db,
        file_category="stamping_tonnage_price",
        stored_relpath=relpath_v2,
        original_filename="b.xlsx",
        current_user=user,
        location="qd",
        year=2026,
    )
    memory_db.commit()
    memory_db.refresh(first)

    assert first.status == "superseded"
    assert first.superseded_by_id == second.id
    assert second.status == "active"


def test_register_welding_unit_price_supersedes_same_scope(
    memory_db: Session, tmp_path: Path
) -> None:
    upload_dir = settings.UPLOAD_DIR
    relpath_v1 = _write_excel(upload_dir, "bom/welding-unit-price/2026/qd/a.xlsx", b"v1")
    relpath_v2 = _write_excel(upload_dir, "bom/welding-unit-price/2026/qd/b.xlsx", b"v2")
    user = _admin_user()

    first = register_existing(
        memory_db,
        file_category="bom_welding_unit_price",
        stored_relpath=relpath_v1,
        original_filename="a.xlsx",
        current_user=user,
        location="qd",
        year=2026,
    )
    memory_db.commit()

    second = register_existing(
        memory_db,
        file_category="bom_welding_unit_price",
        stored_relpath=relpath_v2,
        original_filename="b.xlsx",
        current_user=user,
        location="qd",
        year=2026,
    )
    memory_db.commit()
    memory_db.refresh(first)

    assert first.status == "superseded"
    assert first.superseded_by_id == second.id
    assert second.status == "active"


def test_register_annual_part_price_supersedes_same_scope(
    memory_db: Session, tmp_path: Path
) -> None:
    upload_dir = settings.UPLOAD_DIR
    relpath_v1 = _write_excel(upload_dir, "bom/annual-part-price/2026/qd/a.xlsx", b"v1")
    relpath_v2 = _write_excel(upload_dir, "bom/annual-part-price/2026/qd/b.xlsx", b"v2")
    user = _admin_user()

    first = register_existing(
        memory_db,
        file_category="bom_annual_part_price",
        stored_relpath=relpath_v1,
        original_filename="a.xlsx",
        current_user=user,
        location="qd",
        year=2026,
    )
    memory_db.commit()

    second = register_existing(
        memory_db,
        file_category="bom_annual_part_price",
        stored_relpath=relpath_v2,
        original_filename="b.xlsx",
        current_user=user,
        location="qd",
        year=2026,
    )
    memory_db.commit()
    memory_db.refresh(first)

    assert first.status == "superseded"
    assert first.superseded_by_id == second.id
    assert second.status == "active"


def test_register_existing_supersedes_same_scope(memory_db: Session, tmp_path: Path) -> None:
    upload_dir = settings.UPLOAD_DIR
    relpath_v1 = _write_excel(upload_dir, "bom/qd/t28/v1/a.xlsx", b"v1")
    relpath_v2 = _write_excel(upload_dir, "bom/qd/t28/v1/b.xlsx", b"v2")
    user = _admin_user()

    first = register_existing(
        memory_db,
        file_category="bom_material",
        stored_relpath=relpath_v1,
        original_filename="a.xlsx",
        current_user=user,
        location="qd",
        vehicle_model="t28",
        bom_version="v1",
    )
    memory_db.commit()

    second = register_existing(
        memory_db,
        file_category="bom_material",
        stored_relpath=relpath_v2,
        original_filename="b.xlsx",
        current_user=user,
        location="qd",
        vehicle_model="t28",
        bom_version="v1",
    )
    memory_db.commit()
    memory_db.refresh(first)

    assert first.status == "superseded"
    assert first.superseded_by_id == second.id
    assert second.status == "active"

    active = _repo.list_active_by_scope(
        memory_db,
        file_category="bom_material",
        location="qd",
        vehicle_model="t28",
        bom_version="v1",
    )
    assert len(active) == 1
    assert active[0].id == second.id


def test_path_outside_upload_dir_rejected(memory_db: Session, tmp_path: Path) -> None:
    outside = tmp_path / "outside.xlsx"
    outside.write_bytes(b"x")
    user = _admin_user()
    with pytest.raises(ValueError, match="上传目录"):
        register_existing(
            memory_db,
            file_category="steel_base_price",
            stored_relpath=str(outside),
            original_filename="outside.xlsx",
            current_user=user,
            year=2025,
            month=1,
        )
