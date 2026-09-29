"""
BOM 包装运输费上传源文件归档

按「年度 / 基地 / 项目」存放原始 Excel，便于事后核对，避免扯皮。
规则对齐一事一议钢价（`steel_price_archive`）：时间戳前缀 + 类型标记 + 原文件名。

目录结构：
  uploads/bom/packaging-transport-fee/{year}/{location}/{vehicle_model}/
    {timestamp}_packaging-transport-fee_{原文件名}
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from app.common.period import is_costing_year
from app.common.timezone import now
from app.config import settings

logger = logging.getLogger("utils.bom_packaging_transport_fee_archive")

ARCHIVE_ROOT_NAME = "bom"
ARCHIVE_KIND = "packaging-transport-fee"

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def save_packaging_transport_fee_upload(
    *,
    file_content: bytes,
    filename: str,
    year: int,
    location: str,
    vehicle_model: str,
) -> Path:
    """
    将上传源文件归档到
    uploads/bom/packaging-transport-fee/{year}/{location}/{vehicle_model}/。

    Returns:
        归档后的绝对路径
    """
    if not file_content:
        raise ValueError("归档文件内容为空")
    if not is_costing_year(year):
        raise ValueError(f"无效年度: {year}")

    safe_location = _sanitize_segment(location)
    safe_vehicle = _sanitize_segment(vehicle_model)
    safe_name = _sanitize_filename(filename or "upload.xlsx")
    timestamp = now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{timestamp}_{ARCHIVE_KIND}_{safe_name}"

    target_dir = (
        settings.UPLOAD_DIR
        / ARCHIVE_ROOT_NAME
        / ARCHIVE_KIND
        / str(year)
        / safe_location
        / safe_vehicle
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / archive_name

    target_path.write_bytes(file_content)
    logger.info(
        "包装运输费源文件已归档: year=%s location=%s vehicle=%s path=%s",
        year,
        safe_location,
        safe_vehicle,
        target_path,
    )
    return target_path


def _sanitize_filename(filename: str) -> str:
    """去掉路径成分与不安全字符，保留可追溯的原名。"""
    name = Path(filename).name.strip() or "upload.xlsx"
    name = _UNSAFE_CHARS.sub("_", name)
    name = name.rstrip(". ")
    return name or "upload.xlsx"


def _sanitize_segment(value: str) -> str:
    text = (value or "").strip() or "unknown"
    text = _UNSAFE_CHARS.sub("_", text)
    text = text.replace(" ", "_").rstrip(". ")
    return text or "unknown"
