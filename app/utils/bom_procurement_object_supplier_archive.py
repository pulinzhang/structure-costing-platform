"""采购对象供应商上传源文件归档。"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from app.common.timezone import now
from app.config import settings

logger = logging.getLogger("utils.bom_procurement_object_supplier_archive")

ARCHIVE_ROOT_NAME = "bom"
ARCHIVE_KIND = "procurement-object-supplier"

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def save_procurement_object_supplier_upload(
    *,
    file_content: bytes,
    filename: str,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> Path:
    if not file_content:
        raise ValueError("归档文件内容为空")
    safe_location = _sanitize_segment(location)
    safe_model = _sanitize_segment(vehicle_model)
    safe_version = _sanitize_segment(bom_version)
    safe_name = _sanitize_filename(filename or "upload.xlsx")
    timestamp = now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{timestamp}_{ARCHIVE_KIND}_{safe_name}"
    target_dir = (
        settings.UPLOAD_DIR
        / ARCHIVE_ROOT_NAME
        / ARCHIVE_KIND
        / safe_location
        / safe_model
        / safe_version
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / archive_name
    suffix = 2
    while target_path.exists():
        target_path = target_dir / f"{timestamp}_{ARCHIVE_KIND}_{suffix}_{safe_name}"
        suffix += 1
    target_path.write_bytes(file_content)
    logger.info(
        "采购对象供应商源文件已归档: location=%s vehicle_model=%s bom_version=%s path=%s",
        safe_location,
        safe_model,
        safe_version,
        target_path,
    )
    return target_path


def _sanitize_filename(filename: str) -> str:
    name = Path(filename).name.strip() or "upload.xlsx"
    name = _UNSAFE_CHARS.sub("_", name)
    name = name.rstrip(". ")
    return name or "upload.xlsx"


def _sanitize_segment(value: str) -> str:
    text = (value or "").strip() or "unknown"
    text = _UNSAFE_CHARS.sub("_", text)
    text = text.replace(" ", "_").rstrip(". ")
    return text or "unknown"
