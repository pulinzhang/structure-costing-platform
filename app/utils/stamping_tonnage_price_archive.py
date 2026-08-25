"""
冲压冲次单价上传源文件归档

按「年度 / 基地」存放原始 Excel，便于事后核对。
规则对齐包装运输费 / 一事一议钢价：时间戳前缀 + 类型标记 + 原文件名。

目录结构：
  uploads/stamping/tonnage-price/{year}/{location}/
    {timestamp}_tonnage-price_{原文件名}
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from app.common.timezone import now
from app.config import settings

logger = logging.getLogger("utils.stamping_tonnage_price_archive")

ARCHIVE_ROOT_NAME = "stamping"
ARCHIVE_KIND = "tonnage-price"

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def save_tonnage_price_upload(
    *,
    file_content: bytes,
    filename: str,
    year: int,
    location: str,
) -> Path:
    """
    将上传源文件归档到 uploads/stamping/tonnage-price/{year}/{location}/。

    Returns:
        归档后的绝对路径
    """
    if not file_content:
        raise ValueError("归档文件内容为空")
    if year < 2000 or year > 2100:
        raise ValueError(f"无效年度: {year}")

    safe_location = _sanitize_segment(location)
    safe_name = _sanitize_filename(filename or "upload.xlsx")
    timestamp = now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{timestamp}_{ARCHIVE_KIND}_{safe_name}"

    target_dir = settings.UPLOAD_DIR / ARCHIVE_ROOT_NAME / ARCHIVE_KIND / str(year) / safe_location
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / archive_name

    target_path.write_bytes(file_content)
    logger.info(
        "冲次单价源文件已归档: year=%s location=%s path=%s",
        year,
        safe_location,
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
