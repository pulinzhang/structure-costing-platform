"""嵌入图转为 PNG。

Pillow 只能在 Windows 直接打开 WMF。Excel 简图是 STRETCHDIB 里的位图，Linux 抽 DIB。
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from io import BytesIO
from pathlib import Path

from PIL import Image

logger = logging.getLogger("common.sketch_png")

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_WMF_PLACEABLE = b"\xd7\xcd\xc6\x9a"
_WMF_STANDARD = b"\x01\x00\x09\x00"
_META_STRETCHDIB = 0x0F43
_META_DIBSTRETCHBLT = 0x0B41
_META_DIBBITBLT = 0x0940
_META_SETDIBTODEV = 0x0D33
_META_DIB_FUNCTIONS = frozenset(
    {_META_STRETCHDIB, _META_DIBSTRETCHBLT, _META_DIBBITBLT, _META_SETDIBTODEV}
)
_VALID_BIT_COUNTS = frozenset({1, 4, 8, 16, 24, 32})
_MAX_DIB_EDGE = 20000
_BITMAPINFO_SIZE = 40


def media_bytes_to_png(raw: bytes, media_path: str = "") -> bytes | None:
    """xlsx 内嵌图转 PNG。"""
    if not raw:
        return None
    if raw[:8] == _PNG_MAGIC:
        return raw
    if _is_wmf(raw, media_path):
        png_bytes = _wmf_embedded_dib_to_png(raw)
        if png_bytes:
            return png_bytes
        logger.warning("WMF 简图未抽到位图 %s", Path(media_path).name or "embedded.wmf")
        return None
    png_bytes = _pil_to_png(raw)
    if png_bytes:
        return png_bytes
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
        return _image_to_png_bytes(Image.open(BytesIO(raw)))
    except Exception:
        return None


def _image_to_png_bytes(image: Image.Image) -> bytes:
    if image.mode == "RGBA":
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != "RGB":
        image = image.convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _wmf_embedded_dib_to_png(raw: bytes) -> bytes | None:
    for record in _iter_wmf_dib_records(raw):
        png_bytes = _record_dib_to_png(record)
        if png_bytes:
            return png_bytes
    return None


def _iter_wmf_dib_records(raw: bytes) -> Iterator[bytes]:
    pos = 22 if raw[:4] == _WMF_PLACEABLE else 0
    if pos + 18 > len(raw):
        return
    header_size_words = int.from_bytes(raw[pos + 2 : pos + 4], "little")
    if header_size_words < 9:
        header_size_words = 9
    pos += header_size_words * 2
    while pos + 6 <= len(raw):
        size_words = int.from_bytes(raw[pos : pos + 4], "little")
        func = int.from_bytes(raw[pos + 4 : pos + 6], "little")
        size_bytes = size_words * 2
        if size_words < 3 or pos + size_bytes > len(raw):
            break
        if func in _META_DIB_FUNCTIONS:
            yield raw[pos : pos + size_bytes]
        pos += size_bytes


def _record_dib_to_png(record: bytes) -> bytes | None:
    for offset in range(6, len(record) - _BITMAPINFO_SIZE, 2):
        if int.from_bytes(record[offset : offset + 4], "little") != _BITMAPINFO_SIZE:
            continue
        width = int.from_bytes(record[offset + 4 : offset + 8], "little", signed=True)
        height = int.from_bytes(record[offset + 8 : offset + 12], "little", signed=True)
        planes = int.from_bytes(record[offset + 12 : offset + 14], "little")
        bit_count = int.from_bytes(record[offset + 14 : offset + 16], "little")
        if (
            planes != 1
            or bit_count not in _VALID_BIT_COUNTS
            or not (1 <= abs(width) <= _MAX_DIB_EDGE)
            or not (1 <= abs(height) <= _MAX_DIB_EDGE)
        ):
            continue
        png_bytes = _dib_to_png(record[offset:])
        if png_bytes:
            return png_bytes
    return None


def _dib_to_png(dib: bytes) -> bytes | None:
    if len(dib) < _BITMAPINFO_SIZE:
        return None
    pixel_offset = 14 + _BITMAPINFO_SIZE
    bmp = (
        b"BM"
        + (14 + len(dib)).to_bytes(4, "little")
        + (0).to_bytes(4, "little")
        + pixel_offset.to_bytes(4, "little")
        + dib
    )
    try:
        image = Image.open(BytesIO(bmp))
        image.load()
        return _image_to_png_bytes(image)
    except Exception:
        return None
