"""嵌入图转为 PNG。

Pillow 只能在 Windows 直接打开 WMF/EMF。Excel 简图是 metafile 里的位图，Linux 抽 DIB。
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
_EMF_SIGNATURE = b" EMF"
_META_STRETCHDIB = 0x0F43
_META_DIBSTRETCHBLT = 0x0B41
_META_DIBBITBLT = 0x0940
_META_SETDIBTODEV = 0x0D33
_META_DIB_FUNCTIONS = frozenset(
    {_META_STRETCHDIB, _META_DIBSTRETCHBLT, _META_DIBBITBLT, _META_SETDIBTODEV}
)
_EMR_SETDIBITSTODEVICE = 80
_EMR_STRETCHDIBITS = 81
_EMR_DIB_FUNCTIONS = frozenset({_EMR_SETDIBITSTODEVICE, _EMR_STRETCHDIBITS})
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
    if _is_emf(raw, media_path):
        png_bytes = _emf_embedded_dib_to_png(raw)
        if png_bytes:
            return png_bytes
        logger.warning("EMF 简图未抽到位图 %s", Path(media_path).name or "embedded.emf")
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


def _is_emf(raw: bytes, media_path: str) -> bool:
    suffix = Path(media_path).suffix.lower()
    if suffix == ".emf":
        return True
    return len(raw) >= 44 and raw[40:44] == _EMF_SIGNATURE


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


def _emf_embedded_dib_to_png(raw: bytes) -> bytes | None:
    pos = 0
    while pos + 8 <= len(raw):
        rec_type = int.from_bytes(raw[pos : pos + 4], "little")
        rec_size = int.from_bytes(raw[pos + 4 : pos + 8], "little")
        if rec_size < 8 or pos + rec_size > len(raw):
            break
        if rec_type in _EMR_DIB_FUNCTIONS and rec_size >= 64:
            record = raw[pos : pos + rec_size]
            png_bytes = _emf_stretchdibits_to_png(record)
            if png_bytes:
                return png_bytes
        pos += rec_size
    return None


def _emf_stretchdibits_to_png(record: bytes) -> bytes | None:
    off_bmi = int.from_bytes(record[48:52], "little")
    cb_bmi = int.from_bytes(record[52:56], "little")
    off_bits = int.from_bytes(record[56:60], "little")
    cb_bits = int.from_bytes(record[60:64], "little")
    if cb_bmi < _BITMAPINFO_SIZE or cb_bits <= 0:
        return None
    if off_bmi + cb_bmi > len(record) or off_bits + cb_bits > len(record):
        return None
    bmi = record[off_bmi : off_bmi + cb_bmi]
    bits = record[off_bits : off_bits + cb_bits]
    return _bmi_bits_to_png(bmi, bits)


def _dib_to_png(dib: bytes) -> bytes | None:
    if len(dib) < _BITMAPINFO_SIZE:
        return None
    return _bmi_bits_to_png(dib[:_BITMAPINFO_SIZE], dib[_BITMAPINFO_SIZE:])


def _bmi_bits_to_png(bmi: bytes, bits: bytes) -> bytes | None:
    pixel_offset = 14 + len(bmi)
    bmp = (
        b"BM"
        + (14 + len(bmi) + len(bits)).to_bytes(4, "little")
        + (0).to_bytes(4, "little")
        + pixel_offset.to_bytes(4, "little")
        + bmi
        + bits
    )
    try:
        image = Image.open(BytesIO(bmp))
        image.load()
        return _image_to_png_bytes(image)
    except Exception:
        return None
