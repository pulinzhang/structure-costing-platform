"""工艺确认表 — 简图嵌入。"""

from __future__ import annotations

import logging
from io import BytesIO

from openpyxl.drawing.image import Image as XlImage
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.models.stamping import StampingPart
from app.services.stamping.part.export.constants import (
    _PX_TO_PT,
    DEFAULT_ROW_HEIGHT,
    SKETCH_COL,
    SKETCH_MAX_WIDTH_PX,
    SKETCH_MIN_HEIGHT_PX,
    SKETCH_PAD_PT,
)
from app.services.stamping.part.export.helpers import _resolve_sketch_path

logger = logging.getLogger("service.stamping.part.export")


def embed_sketch(
    ws: Worksheet,
    *,
    part: StampingPart,
    start_row: int,
    n_rows: int,
    sketch_buffers: list[BytesIO],
) -> bool:
    """把零件简图锚定到短码后的简图列合并格左上角，按格缩放；缺文件则跳过。"""
    sketch_path = _resolve_sketch_path(part)
    if sketch_path is None:
        return False
    try:
        payload = BytesIO(sketch_path.read_bytes())
        xl_img = XlImage(payload)
        payload.seek(0)
        sketch_buffers.append(payload)
    except Exception as exc:
        logger.warning("读取零件简图失败 %s: %s", part.part_number, exc)
        return False

    orig_w = float(xl_img.width or 0)
    orig_h = float(xl_img.height or 0)
    if orig_w <= 0 or orig_h <= 0:
        return False

    available_h = max(
        SKETCH_MIN_HEIGHT_PX,
        n_rows * DEFAULT_ROW_HEIGHT / _PX_TO_PT - SKETCH_PAD_PT,
    )
    scale = min(SKETCH_MAX_WIDTH_PX / orig_w, available_h / orig_h, 1.0)
    xl_img.width = max(1, int(orig_w * scale))
    xl_img.height = max(1, int(orig_h * scale))

    needed_pt = xl_img.height * _PX_TO_PT + SKETCH_PAD_PT
    current_pt = n_rows * DEFAULT_ROW_HEIGHT
    if needed_pt > current_pt:
        each_pt = needed_pt / n_rows
        for offset in range(n_rows):
            ws.row_dimensions[start_row + offset].height = each_pt

    xl_img.anchor = f"{get_column_letter(SKETCH_COL)}{start_row}"
    ws.add_image(xl_img)
    return True
