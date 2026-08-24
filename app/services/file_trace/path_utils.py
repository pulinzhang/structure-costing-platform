"""UPLOAD_DIR 路径校验与相对路径转换。"""

from __future__ import annotations

from pathlib import Path

from app.config import settings


def resolve_upload_path(stored_relpath: str) -> Path:
    """校验相对路径在 UPLOAD_DIR 内，禁止 .. 逃逸。"""
    text = (stored_relpath or "").strip().replace("\\", "/")
    if not text or ".." in text.split("/"):
        raise ValueError("无效的文件路径")
    upload_root = settings.UPLOAD_DIR.resolve()
    absolute = (upload_root / text).resolve()
    if upload_root not in absolute.parents and absolute != upload_root:
        raise ValueError("文件路径超出上传目录")
    return absolute


def to_upload_relpath(absolute_path: Path | str) -> str:
    """绝对路径 → 相对 UPLOAD_DIR 的正斜杠路径。"""
    upload_root = settings.UPLOAD_DIR.resolve()
    target = Path(absolute_path).resolve()
    try:
        relative = target.relative_to(upload_root)
    except ValueError as exc:
        raise ValueError("文件不在上传目录内") from exc
    return str(relative).replace("\\", "/")
