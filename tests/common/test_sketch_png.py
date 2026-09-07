"""嵌入图转 PNG：直通 PNG、Pillow、以及 Linux wmf2gd 回退。"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from app.common.sketch_png import media_bytes_to_png

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_WMF_PLACEABLE = b"\xd7\xcd\xc6\x9a"


def _tiny_png() -> bytes:
    image = Image.new("RGB", (2, 2), (255, 255, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    png = buffer.getvalue()
    assert png[:8] == _PNG_MAGIC
    return png


def test_png_passthrough() -> None:
    png = _tiny_png()
    assert media_bytes_to_png(png, "xl/media/image7.png") == png


def test_empty_returns_none() -> None:
    assert media_bytes_to_png(b"", "xl/media/image11.wmf") is None


def test_wmf_without_wmf2gd_returns_none() -> None:
    raw = _WMF_PLACEABLE + b"\x00" * 32
    with patch("app.common.sketch_png.shutil.which", return_value=None):
        assert media_bytes_to_png(raw, "xl/media/image11.wmf") is None


def test_wmf_uses_wmf2gd_on_linux_fallback() -> None:
    png = _tiny_png()
    raw = _WMF_PLACEABLE + b"\x00" * 32
    completed = MagicMock()
    completed.returncode = 0
    completed.stderr = b""

    def fake_run(args: list[str], **_kwargs: object) -> MagicMock:
        dest = Path(args[args.index("-o") + 1])
        dest.write_bytes(png)
        return completed

    with (
        patch("app.common.sketch_png.shutil.which", return_value="/usr/bin/wmf2gd"),
        patch("app.common.sketch_png.subprocess.run", side_effect=fake_run) as run,
    ):
        result = media_bytes_to_png(raw, "xl/media/image11.wmf")

    assert result == png
    assert run.call_args.args[0][0] == "/usr/bin/wmf2gd"
    assert "-t" in run.call_args.args[0]
