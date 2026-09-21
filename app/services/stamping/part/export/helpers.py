"""简图路径、数字单元格、纵向合并、导出字体。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from openpyxl.styles import Alignment, Font

from app.common.money import excel_money_cell
from app.config import settings
from app.models.stamping import StampingPart
from app.services.stamping.part.export.constants import _FONT_NAME


class PartExportStyleTarget(Protocol):
    """`PartExportStyle.bind` 写入的对齐/字体。"""

    _center: Alignment
    _left: Alignment
    _right: Alignment
    _header_font: Font
    _title_font: Font
    _meta_font: Font
    _data_font: Font
    _mute_header_font: Font
    _mute_data_font: Font
    _short_code_font: Font


class PartExportStyle:
    """工艺确认表与钢材测算共用的对齐/字体。"""

    def __init__(self) -> None:
        self.center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        self.left = Alignment(horizontal="left", vertical="center", wrap_text=True)
        self.right = Alignment(horizontal="right", vertical="center")
        self.header_font = Font(name=_FONT_NAME, size=10, bold=True, color="FFFFFF")
        self.title_font = Font(name=_FONT_NAME, size=14, bold=True, color="FFFFFF")
        self.meta_font = Font(name=_FONT_NAME, size=10, color="1F4E79")
        self.data_font = Font(name=_FONT_NAME, size=9, color="000000")
        self.mute_header_font = Font(name=_FONT_NAME, size=9, color="6B6B6B")
        self.mute_data_font = Font(name=_FONT_NAME, size=8, color="8A8A8A")
        self.short_code_font = Font(name=_FONT_NAME, size=10, bold=True, color="1F4E79")

    def bind(self, target: PartExportStyleTarget) -> None:
        target._center = self.center
        target._left = self.left
        target._right = self.right
        target._header_font = self.header_font
        target._title_font = self.title_font
        target._meta_font = self.meta_font
        target._data_font = self.data_font
        target._mute_header_font = self.mute_header_font
        target._mute_data_font = self.mute_data_font
        target._short_code_font = self.short_code_font


def _resolve_sketch_path(part: StampingPart) -> Path | None:
    """按上传约定取简图：UPLOAD_DIR/{基地}/{车型}/{版本}/{零件号}.png。"""
    location = (part.location or "").strip()
    vehicle_model = (part.vehicle_model or "").strip()
    version = (part.version or "").strip()
    part_number = (part.part_number or "").strip()
    if not location or not vehicle_model or not version or not part_number:
        return None
    safe_location = location.replace("/", "_").replace("\\", "_")
    safe_vehicle = vehicle_model.replace("/", "_").replace("\\", "_")
    safe_version = version.replace("/", "_").replace("\\", "_").replace(" ", "_")
    safe_name = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in part_number)
    if not safe_name:
        return None
    candidate = (
        settings.UPLOAD_DIR / safe_location / safe_vehicle / safe_version / f"{safe_name}.png"
    )
    if candidate.is_file():
        return candidate
    return None


def _num(value: Any, quant: Any) -> Any:
    return excel_money_cell(value, quant)


def _merge_if_needed(ws: Any, start_row: int, end_row: int, col: int) -> None:
    if end_row > start_row:
        ws.merge_cells(
            start_row=start_row,
            start_column=col,
            end_row=end_row,
            end_column=col,
        )


def _split_spans(n_rows: int, n_blanks: int) -> list[tuple[int, int]]:
    """把零件占用行按子片数切成连续块（0-based 闭区间）。"""
    if n_blanks <= 0:
        return []
    base, extra = divmod(n_rows, n_blanks)
    spans: list[tuple[int, int]] = []
    start = 0
    for index in range(n_blanks):
        size = max(base + (1 if index < extra else 0), 1)
        end = min(start + size - 1, n_rows - 1)
        spans.append((start, end))
        start = end + 1
        if start >= n_rows:
            while len(spans) < n_blanks:
                spans.append((n_rows - 1, n_rows - 1))
            break
    return spans
