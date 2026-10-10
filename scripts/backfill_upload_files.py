"""
定向回填 upload_files 登记（幂等）。

用法：
    python -X utf8 -m scripts.backfill_upload_files
    python -X utf8 -m scripts.backfill_upload_files --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.audit import SYSTEM_USER, audit_create
from app.config import settings
from app.database import SessionLocal
from app.models.bom.node import BomSnapshot
from app.repositories.file_trace.upload_file_repository import (
    UploadFileInsert,
    UploadFileRepository,
)
from app.services.file_trace.path_utils import resolve_upload_path, to_upload_relpath
from app.utils.steel_price_archive import FILE_KIND_BASE_PRICE, FILE_KIND_POLICY

logger = logging.getLogger("scripts.backfill_upload_files")
_repo = UploadFileRepository()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _register_row(
    db: Session,
    *,
    file_category: str,
    stored_relpath: str,
    original_filename: str,
    location: str | None = None,
    year: int | None = None,
    month: int | None = None,
    vehicle_model: str | None = None,
    bom_version: str | None = None,
    process_version: str | None = None,
    stamping_supplier: str | None = None,
    business_ref_type: str | None = None,
    business_ref_id: int | None = None,
    dry_run: bool = False,
) -> str:
    existing = _repo.get_by_relpath(db, stored_relpath)
    if existing:
        return "skip"

    try:
        absolute = resolve_upload_path(stored_relpath)
    except ValueError:
        absolute = None

    status = "active"
    file_hash = ""
    file_size = 0
    extension = Path(original_filename).suffix.lower()

    if absolute and absolute.is_file():
        file_hash = _file_hash(absolute)
        file_size = absolute.stat().st_size
    else:
        status = "missing"

    if dry_run:
        logger.info("[dry-run] %s %s status=%s", file_category, stored_relpath, status)
        return "dry"

    active_rows = _repo.list_active_by_scope(
        db,
        file_category=file_category,
        location=location,
        year=year,
        month=month,
        vehicle_model=vehicle_model,
        bom_version=bom_version,
        process_version=process_version,
        stamping_supplier=stamping_supplier,
    )

    audit = audit_create(SYSTEM_USER)
    row = _repo.create(
        db,
        UploadFileInsert(
            file_category=file_category,
            original_filename=original_filename,
            stored_relpath=stored_relpath,
            file_hash=file_hash or "0" * 64,
            file_size=file_size,
            extension=extension or ".xlsx",
            location=location,
            year=year,
            month=month,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            process_version=process_version,
            stamping_supplier=stamping_supplier,
            business_ref_type=business_ref_type,
            business_ref_id=business_ref_id,
            status=status,
            created_by=audit["created_by"],
            updated_by=audit["updated_by"],
        ),
    )
    if active_rows:
        _repo.mark_superseded(
            active_rows,
            superseded_by_id=row.id,
            updated_by=audit["updated_by"],
        )
    return "create"


def backfill_bom_snapshots(db: Session, *, dry_run: bool) -> dict[str, int]:
    stats = {"create": 0, "skip": 0, "dry": 0}
    snapshots = (
        db.query(BomSnapshot)
        .filter(BomSnapshot.source_file_path.isnot(None))
        .order_by(BomSnapshot.created_at.asc(), BomSnapshot.id.asc())
        .all()
    )
    for snapshot in snapshots:
        relpath = (snapshot.source_file_path or "").replace("\\", "/")
        if not relpath:
            continue
        result = _register_row(
            db,
            file_category="bom_material",
            stored_relpath=relpath,
            original_filename=snapshot.source_filename or Path(relpath).name,
            location=snapshot.location,
            vehicle_model=snapshot.vehicle_model,
            bom_version=snapshot.bom_version,
            business_ref_type="bom_snapshot",
            business_ref_id=snapshot.id,
            dry_run=dry_run,
        )
        stats[result] = stats.get(result, 0) + 1
    return stats


def backfill_steel_price(db: Session, *, dry_run: bool) -> dict[str, int]:
    stats = {"create": 0, "skip": 0, "dry": 0}
    root = settings.UPLOAD_DIR / "steel-price"
    if not root.is_dir():
        return stats

    for year_dir in sorted(root.iterdir()):
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        for month_dir in sorted(year_dir.iterdir()):
            if not month_dir.is_dir():
                continue
            try:
                month = int(month_dir.name)
            except ValueError:
                continue
            for file_path in sorted(month_dir.glob("*.xls*")):
                name = file_path.name
                if f"_{FILE_KIND_BASE_PRICE}_" in name:
                    category = "steel_base_price"
                elif f"_{FILE_KIND_POLICY}_" in name:
                    category = "steel_price_policy"
                else:
                    continue
                relpath = to_upload_relpath(file_path)
                original = name.split("_", 2)[-1] if "_" in name else name
                result = _register_row(
                    db,
                    file_category=category,
                    stored_relpath=relpath,
                    original_filename=original,
                    year=year,
                    month=month,
                    dry_run=dry_run,
                )
                stats[result] = stats.get(result, 0) + 1
    return stats


def backfill_packaging_transport_fee(db: Session, *, dry_run: bool) -> dict[str, int]:
    stats = {"create": 0, "skip": 0, "dry": 0}
    root = settings.UPLOAD_DIR / "bom" / "packaging-transport-fee"
    if not root.is_dir():
        return stats

    for file_path in sorted(root.rglob("*.xls*")):
        if file_path.suffix.lower() not in {".xlsx", ".xls"}:
            continue
        parts = file_path.relative_to(root).parts
        year = None
        location = None
        vehicle_model = None
        if len(parts) >= 3:
            try:
                year = int(parts[0])
                location = parts[1]
                vehicle_model = parts[2]
            except (ValueError, IndexError):
                pass
        relpath = to_upload_relpath(file_path)
        result = _register_row(
            db,
            file_category="bom_packaging_transport_fee",
            stored_relpath=relpath,
            original_filename=file_path.name,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            dry_run=dry_run,
        )
        stats[result] = stats.get(result, 0) + 1
    return stats


def backfill_tonnage_price(db: Session, *, dry_run: bool) -> dict[str, int]:
    stats = {"create": 0, "skip": 0, "dry": 0}
    root = settings.UPLOAD_DIR / "stamping" / "tonnage-price"
    if not root.is_dir():
        return stats

    for file_path in sorted(root.rglob("*.xls*")):
        if file_path.suffix.lower() not in {".xlsx", ".xls"}:
            continue
        parts = file_path.relative_to(root).parts
        year = None
        location = None
        if len(parts) >= 2:
            try:
                year = int(parts[0])
                location = parts[1]
            except (ValueError, IndexError):
                pass
        name = file_path.name
        original = name.split("_", 2)[-1] if name.count("_") >= 2 else name
        relpath = to_upload_relpath(file_path)
        result = _register_row(
            db,
            file_category="stamping_tonnage_price",
            stored_relpath=relpath,
            original_filename=original,
            year=year,
            location=location,
            dry_run=dry_run,
        )
        stats[result] = stats.get(result, 0) + 1
    return stats


def backfill_welding_unit_price(db: Session, *, dry_run: bool) -> dict[str, int]:
    stats = {"create": 0, "skip": 0, "dry": 0}
    root = settings.UPLOAD_DIR / "bom" / "welding-unit-price"
    if not root.is_dir():
        return stats

    for file_path in sorted(root.rglob("*.xls*")):
        if file_path.suffix.lower() not in {".xlsx", ".xls"}:
            continue
        parts = file_path.relative_to(root).parts
        year = None
        location = None
        if len(parts) >= 2:
            try:
                year = int(parts[0])
                location = parts[1]
            except (ValueError, IndexError):
                pass
        name = file_path.name
        original = name.split("_", 2)[-1] if name.count("_") >= 2 else name
        relpath = to_upload_relpath(file_path)
        result = _register_row(
            db,
            file_category="bom_welding_unit_price",
            stored_relpath=relpath,
            original_filename=original,
            year=year,
            location=location,
            dry_run=dry_run,
        )
        stats[result] = stats.get(result, 0) + 1
    return stats


def backfill_annual_part_price(db: Session, *, dry_run: bool) -> dict[str, int]:
    stats = {"create": 0, "skip": 0, "dry": 0}
    root = settings.UPLOAD_DIR / "bom" / "annual-part-price"
    if not root.is_dir():
        return stats

    for file_path in sorted(root.rglob("*.xls*")):
        if file_path.suffix.lower() not in {".xlsx", ".xls"}:
            continue
        parts = file_path.relative_to(root).parts
        year = None
        location = None
        if len(parts) >= 2:
            try:
                year = int(parts[0])
                location = parts[1]
            except (ValueError, IndexError):
                pass
        name = file_path.name
        original = name.split("_", 2)[-1] if name.count("_") >= 2 else name
        relpath = to_upload_relpath(file_path)
        result = _register_row(
            db,
            file_category="bom_annual_part_price",
            stored_relpath=relpath,
            original_filename=original,
            year=year,
            location=location,
            dry_run=dry_run,
        )
        stats[result] = stats.get(result, 0) + 1
    return stats


def backfill_stamping_process(db: Session, *, dry_run: bool) -> dict[str, int]:
    stats = {"create": 0, "skip": 0, "dry": 0}
    upload_root = settings.UPLOAD_DIR.resolve()
    skip_names = {"bom", "steel-price", "avatars", "stamping"}

    for location_dir in sorted(upload_root.iterdir()):
        if not location_dir.is_dir() or location_dir.name in skip_names:
            continue
        for vehicle_dir in sorted(location_dir.iterdir()):
            if not vehicle_dir.is_dir():
                continue
            for version_dir in sorted(vehicle_dir.iterdir()):
                if not version_dir.is_dir():
                    continue
                for file_path in sorted(version_dir.glob("*.xls*")):
                    relpath = to_upload_relpath(file_path)
                    result = _register_row(
                        db,
                        file_category="stamping_process",
                        stored_relpath=relpath,
                        original_filename=file_path.name,
                        location=location_dir.name,
                        vehicle_model=vehicle_dir.name,
                        process_version=version_dir.name,
                        dry_run=dry_run,
                    )
                    stats[result] = stats.get(result, 0) + 1
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="回填 upload_files 登记")
    parser.add_argument("--dry-run", action="store_true", help="仅打印，不写库")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    db = SessionLocal()
    try:
        totals = {"create": 0, "skip": 0, "dry": 0}
        for name, func in (
            ("bom_snapshots", backfill_bom_snapshots),
            ("steel_price", backfill_steel_price),
            ("packaging_transport_fee", backfill_packaging_transport_fee),
            ("welding_unit_price", backfill_welding_unit_price),
            ("annual_part_price", backfill_annual_part_price),
            ("tonnage_price", backfill_tonnage_price),
            ("stamping_process", backfill_stamping_process),
        ):
            stats = func(db, dry_run=args.dry_run)
            logger.info("%s => %s", name, stats)
            for key, value in stats.items():
                totals[key] = totals.get(key, 0) + value
        if not args.dry_run:
            db.commit()
        logger.info("done => %s", totals)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
