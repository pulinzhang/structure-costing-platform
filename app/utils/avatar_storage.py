"""
用户头像存储

目录：
  uploads/avatars/
    u{user_id}_{timestamp}_{uuid}{ext}

对外访问：
  /uploads/avatars/{filename}
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from app.common.timezone import now
from app.config import settings

logger = logging.getLogger("utils.avatar_storage")

AVATAR_DIR_NAME = "avatars"
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2MB
AVATAR_URL_PREFIX = "/uploads/avatars/"


def get_avatar_dir() -> Path:
    target = settings.UPLOAD_DIR / AVATAR_DIR_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target


def is_custom_avatar_url(avatar_url: str | None) -> bool:
    if not avatar_url:
        return False
    return avatar_url.startswith(AVATAR_URL_PREFIX)


def save_user_avatar(
    *,
    user_id: int,
    file_content: bytes,
    filename: str,
) -> str:
    """
    保存用户头像到 uploads/avatars/，返回可访问 URL。
    """
    if not file_content:
        raise ValueError("头像文件为空")
    if len(file_content) > MAX_AVATAR_BYTES:
        raise ValueError("头像文件不能超过 2MB")

    suffix = Path(filename or "").suffix.lower()
    if suffix not in ALLOWED_AVATAR_EXTENSIONS:
        raise ValueError("仅支持 jpg / jpeg / png / webp / gif 格式")

    safe_name = f"u{user_id}_{now().strftime('%Y%m%d_%H%M%S')}" f"_{uuid.uuid4().hex[:8]}{suffix}"
    target_path = get_avatar_dir() / safe_name
    target_path.write_bytes(file_content)
    url = f"{AVATAR_URL_PREFIX}{safe_name}"
    logger.info("用户头像已保存: user_id=%s path=%s", user_id, target_path)
    return url


def delete_avatar_file(avatar_url: str | None) -> None:
    """删除 uploads/avatars 下的旧头像（忽略默认/外部路径）"""
    if not avatar_url or not is_custom_avatar_url(avatar_url):
        return
    filename = Path(avatar_url).name
    if not filename or filename in {".", ".."}:
        return
    target = get_avatar_dir() / filename
    try:
        if target.is_file():
            target.unlink()
            logger.info("已删除旧头像: %s", target)
    except OSError as exc:
        logger.warning("删除旧头像失败: %s (%s)", target, exc)
