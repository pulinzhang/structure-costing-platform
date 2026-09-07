"""嵌入图转为 PNG。

Pillow 只能在 Windows 打开 WMF；Linux 容器用 libwmf-bin 的 wmf2gd。
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image

logger = logging.getLogger("common.sketch_png")

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_WMF_PLACEABLE = b"\xd7\xcd\xc6\x9a"
_WMF_STANDARD = b"\x01\x00\x09\x00"
_WMF2GD_TIMEOUT_SEC = 60


def media_bytes_to_png(raw: bytes, media_path: str = "") -> bytes | None:
    """xlsx 内嵌图转 PNG；WMF 在 Linux 走 wmf2gd。"""
    if not raw:
        return None
    if raw[:8] == _PNG_MAGIC:
        return raw

    png_bytes = _pil_to_png(raw)
    if png_bytes:
        return png_bytes
    if _is_wmf(raw, media_path):
        return _wmf_to_png_libwmf(raw, media_path)
    logger.warning("简图转 PNG 失败 %s", Path(media_path).name or "embedded")
    return None


def _is_wmf(raw: bytes, media_path: str) -> bool:
    suffix = Path(media_path).suffix.lower()
    if suffix == ".wmf":
        return True
    if len(raw) < 4:
        return False
    return raw[:4] in {_WMF_PLACEABLE, _WMF_STANDARD}


def _pil_to_png(raw: bytes) -> bytes | None:
    try:
        image: Image.Image = Image.open(BytesIO(raw))
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        elif image.mode != "RGB":
            image = image.convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception:
        return None


def _wmf_to_png_libwmf(raw: bytes, media_path: str) -> bytes | None:
    wmf2gd = shutil.which("wmf2gd")
    if not wmf2gd:
        logger.warning(
            "WMF 简图无法转换 %s：Linux 需安装 libwmf-bin（wmf2gd）",
            Path(media_path).name or "embedded.wmf",
        )
        return None

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.wmf"
        dest = Path(tmp) / "out.png"
        src.write_bytes(raw)
        try:
            completed = subprocess.run(
                [
                    wmf2gd,
                    "--wmf-ignore-nonfatal=yes",
                    "--maxwidth=1600",
                    "--maxheight=1600",
                    "--maxpect",
                    "-t",
                    "png",
                    "-o",
                    str(dest),
                    str(src),
                ],
                capture_output=True,
                timeout=_WMF2GD_TIMEOUT_SEC,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning(
                "wmf2gd 无法执行 %s: %s",
                Path(media_path).name or "embedded.wmf",
                exc,
            )
            return None
        if completed.returncode != 0 or not dest.is_file() or dest.stat().st_size == 0:
            stderr = completed.stderr.decode("utf-8", errors="replace")[:300]
            logger.warning(
                "wmf2gd 失败 %s code=%s %s",
                Path(media_path).name or "embedded.wmf",
                completed.returncode,
                stderr,
            )
            return None
        png_bytes = dest.read_bytes()
        if png_bytes[:8] == _PNG_MAGIC:
            return png_bytes
        return _pil_to_png(png_bytes)
