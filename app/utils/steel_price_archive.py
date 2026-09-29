"""
钢价上传源文件归档

按「年度 / 月份」成对存放基准价与加减价政策原始 Excel，
便于事后核对，避免扯皮。

目录结构：
  uploads/steel-price/{year}/{month:02d}/
    {timestamp}_base-price_{原文件名}
    {timestamp}_policy_{原文件名}
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from app.common.period import MONTH_MAX, MONTH_MIN, is_costing_year
from app.common.timezone import now
from app.config import settings

logger = logging.getLogger("utils.steel_price_archive")

ARCHIVE_ROOT_NAME = "steel-price"
FILE_KIND_BASE_PRICE = "base-price"
FILE_KIND_POLICY = "policy"

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def save_steel_price_upload(
    *,
    file_content: bytes,
    filename: str,
    year: int,
    month: int,
    file_kind: str,
) -> Path:
    """
    将上传源文件归档到 uploads/steel-price/{year}/{month}/。

    Args:
        file_content: 文件二进制内容
        filename: 原始文件名
        year: 生效年度
        month: 生效月份（1-12）
        file_kind: ``base-price`` 或 ``policy``

    Returns:
        归档后的绝对路径
    """
    if not file_content:
        raise ValueError("归档文件内容为空")
    if not is_costing_year(year):
        raise ValueError(f"无效年度: {year}")
    if month < MONTH_MIN or month > MONTH_MAX:
        raise ValueError(f"无效月份: {month}")
    if file_kind not in {FILE_KIND_BASE_PRICE, FILE_KIND_POLICY}:
        raise ValueError(f"未知归档类型: {file_kind}")

    safe_name = _sanitize_filename(filename or "upload.xlsx")
    timestamp = now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"{timestamp}_{file_kind}_{safe_name}"

    target_dir = settings.UPLOAD_DIR / ARCHIVE_ROOT_NAME / str(year) / f"{month:02d}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / archive_name

    target_path.write_bytes(file_content)
    logger.info(
        "钢价源文件已归档: kind=%s year=%s month=%02d path=%s",
        file_kind,
        year,
        month,
        target_path,
    )
    return target_path


def _sanitize_filename(filename: str) -> str:
    """去掉路径成分与不安全字符，保留可追溯的原名。"""
    name = Path(filename).name.strip() or "upload.xlsx"
    name = _UNSAFE_CHARS.sub("_", name)
    # Windows 保留名、尾部点空格
    name = name.rstrip(". ")
    return name or "upload.xlsx"
