"""工程变更种树简图：本张有图用新图；换号后不准抄旧号图。"""

from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.parsers.bom.bom_parser import BomParsedNode


def copied_sketch_url(
    *,
    location: str,
    vehicle_model: str,
    bom_version: str,
    part_number: str,
    file_row: BomParsedNode | None,
    old_sketch_url: str | None,
    copy_old_sketch: bool = True,
) -> str | None:
    if file_row is not None and file_row.sketch_bytes:
        return _write_sketch_png(
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            sort_no=file_row.sort_no,
            png_bytes=file_row.sketch_bytes,
        )
    if copy_old_sketch:
        return old_sketch_url
    return None


def _write_sketch_png(
    *,
    location: str,
    vehicle_model: str,
    bom_version: str,
    part_number: str,
    sort_no: int,
    png_bytes: bytes | None,
) -> str | None:
    if not png_bytes:
        return None
    safe_location = _safe_segment(location)
    safe_vehicle = _safe_segment(vehicle_model)
    safe_version = _safe_segment(bom_version)
    relative_dir = Path("bom") / safe_location / safe_vehicle / safe_version / "sketches"
    target_dir = settings.UPLOAD_DIR / relative_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_part = (
        "".join(
            ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in (part_number or "assembly")
        )
        or "assembly"
    )
    file_name = f"{sort_no}_{safe_part}.png"
    (target_dir / file_name).write_bytes(png_bytes)
    return str(relative_dir / file_name).replace("\\", "/")


def _safe_segment(value: str) -> str:
    text = (value or "").strip() or "unknown"
    for ch in ("/", "\\", ":", "*", "?", '"', "<", ">", "|", " "):
        text = text.replace(ch, "_")
    return text
