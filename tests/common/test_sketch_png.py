"""嵌入图转 PNG：直通 PNG、抽 WMF 内嵌 DIB。"""

from __future__ import annotations

from io import BytesIO

from PIL import Image

from app.common.sketch_png import media_bytes_to_png

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_WMF_PLACEABLE = b"\xd7\xcd\xc6\x9a"


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "little")


def _u32(value: int) -> bytes:
    return value.to_bytes(4, "little")


def _tiny_png() -> bytes:
    image = Image.new("RGB", (2, 2), (255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    png = buffer.getvalue()
    assert png[:8] == _PNG_MAGIC
    return png


def _tiny_dib() -> bytes:
    header = bytearray(40)
    header[0:4] = _u32(40)
    header[4:8] = _u32(2)
    header[8:12] = _u32(2)
    header[12:14] = _u16(1)
    header[14:16] = _u16(24)
    row = b"\x00\x00\xff\x00\xff\x00\x00\x00"
    return bytes(header) + row + row


def _stretchdib_wmf(dib: bytes) -> bytes:
    placeable = _WMF_PLACEABLE + b"\x00" * 18
    header = _u16(1) + _u16(9) + _u16(0x300) + _u32(0) + _u16(0) + _u32(0) + _u16(0)
    fields = _u32(0x00CC0020) + _u16(0)
    fields += _u16(2) + _u16(2) + _u16(0) + _u16(0)
    fields += _u16(2) + _u16(2) + _u16(0) + _u16(0)
    body = fields + dib
    if len(body) % 2:
        body += b"\x00"
    record = _u32((6 + len(body)) // 2) + _u16(0x0F43) + body
    return placeable + header + record


def test_png_passthrough() -> None:
    png = _tiny_png()
    assert media_bytes_to_png(png, "xl/media/image7.png") == png


def test_empty_returns_none() -> None:
    assert media_bytes_to_png(b"", "xl/media/image11.wmf") is None


def test_wmf_without_dib_returns_none() -> None:
    raw = _WMF_PLACEABLE + b"\x00" * 32
    assert media_bytes_to_png(raw, "xl/media/image11.wmf") is None


def test_stretchdib_wmf_extracts_dib() -> None:
    png = media_bytes_to_png(_stretchdib_wmf(_tiny_dib()), "xl/media/image11.wmf")
    assert png is not None
    assert png[:8] == _PNG_MAGIC
    image = Image.open(BytesIO(png))
    assert image.size == (2, 2)
