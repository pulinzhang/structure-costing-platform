"""冲压零件主子表 Excel 导出（对齐工艺确认表版式）。

主表：零件字段纵向合并。
子表一：工序（工序名称 / 代号 / 套数 / 吨位 / 费用比例）。
子表二：拼焊子片（料厚 / 长宽按片拆分；无拼焊则与主表同高合并）。
"""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XlImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.common.money import Q2, Q4, excel_money_cell
from app.common.timezone import now
from app.config import settings
from app.exceptions import BusinessException
from app.models.stamping import StampingPart, StampingProcess, StampingTailorWeldBlank
from app.repositories.stamping.stamping_part_repository import StampingPartRepository

logger = logging.getLogger("service.stamping.part_export")

COL_COUNT = 20
DATA_START_ROW = 6
SKETCH_COL = 4
DEFAULT_ROW_HEIGHT = 18
# 简图列加宽，约 130px，给 PNG 留出可视区域
SKETCH_COL_WIDTH = 18
SKETCH_MAX_WIDTH_PX = 118
SKETCH_MIN_HEIGHT_PX = 88
SKETCH_PAD_PT = 8
_PX_TO_PT = 72 / 96

_HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
_SUB_HEADER_FILL = PatternFill("solid", fgColor="2E75B6")
_TITLE_FILL = PatternFill("solid", fgColor="1F4E79")
_META_FILL = PatternFill("solid", fgColor="D6EAF8")
_ZEBRA = PatternFill("solid", fgColor="F2F2F2")
_THIN = Border(
    left=Side(style="thin", color="BFBFBF"),
    right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"),
    bottom=Side(style="thin", color="BFBFBF"),
)
_FONT_NAME = "微软雅黑"

WIDTHS = [
    6,
    16,
    18,
    SKETCH_COL_WIDTH,
    14,
    10,
    10,
    12,
    12,
    10,
    12,
    12,
    14,
    8,
    10,
    10,
    10,
    10,
    16,
    10,
]


class StampingPartExportService:
    """按当前筛选导出冲压工艺确认表（零件 + 工序 + 拼焊子片）。"""

    def __init__(self) -> None:
        self.repository = StampingPartRepository()
        self._center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        self._left = Alignment(horizontal="left", vertical="center", wrap_text=True)
        self._right = Alignment(horizontal="right", vertical="center")
        self._header_font = Font(name=_FONT_NAME, size=10, bold=True, color="FFFFFF")
        self._title_font = Font(name=_FONT_NAME, size=14, bold=True, color="FFFFFF")
        self._meta_font = Font(name=_FONT_NAME, size=10, color="1F4E79")
        self._data_font = Font(name=_FONT_NAME, size=9, color="000000")

    def export(
        self,
        db: Session,
        *,
        location: str,
        stamping_supplier: str,
        vehicle_model: str,
        version: str,
        part_number: str | None = None,
    ) -> tuple[bytes, str]:
        location = location.strip()
        stamping_supplier = stamping_supplier.strip()
        vehicle_model = vehicle_model.strip()
        version = version.strip()
        if not location or not stamping_supplier or not vehicle_model or not version:
            raise BusinessException("导出须同时选定基地、冲压工厂、车型和版本")

        parts = self.repository.list_for_export(
            db,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number.strip() if part_number else None,
        )

        wb = Workbook()
        ws = wb.worksheets[0]
        ws.title = "冲压工艺确认表"

        title = f"{vehicle_model}车身件项目冲压工艺确认表-{stamping_supplier}"
        company = f"冲压承制公司：{stamping_supplier}"
        self._write_banner(ws, title=title, company=company, version=version)
        self._write_headers(ws)

        row_idx = DATA_START_ROW
        process_count = 0
        blank_count = 0
        sketch_count = 0
        sketch_buffers: list[BytesIO] = []
        for seq_no, part in enumerate(parts, start=1):
            processes = sorted(
                list(part.processes or []),
                key=lambda item: (item.process_order or 0, item.id or 0),
            )
            blanks = sorted(
                list(part.tailor_weld_blanks or []),
                key=lambda item: (item.blank_seq or 0, item.id or 0),
            )
            process_count += len(processes)
            blank_count += len(blanks)
            used, has_sketch = self._write_part_block(
                ws,
                start_row=row_idx,
                seq_no=part.seq_no or seq_no,
                part=part,
                processes=processes,
                blanks=blanks,
                zebra=seq_no % 2 == 0,
                sketch_buffers=sketch_buffers,
            )
            if has_sketch:
                sketch_count += 1
            row_idx += used

        for idx, width in enumerate(WIDTHS, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = width
        ws.freeze_panes = f"A{DATA_START_ROW}"
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 90

        buffer = BytesIO()
        try:
            wb.save(buffer)
            content = buffer.getvalue()
        finally:
            sketch_buffers.clear()

        scope = f"{location}_{stamping_supplier}_{vehicle_model}_{version}"
        stamp = now().strftime("%Y%m%d_%H%M%S")
        filename = f"冲压工艺确认表_{scope}_{stamp}.xlsx"
        logger.info(
            "导出冲压工艺 %s 件 / %s 道工序 / %s 片子片 / %s 张简图 / 文件 %s",
            len(parts),
            process_count,
            blank_count,
            sketch_count,
            filename,
        )
        return content, filename

    def _write_banner(self, ws: Any, *, title: str, company: str, version: str) -> None:
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=COL_COUNT)
        c1 = ws.cell(row=1, column=1, value=title)
        c1.font = self._title_font
        c1.fill = _TITLE_FILL
        c1.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[1].height = 28

        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=14)
        c2 = ws.cell(row=2, column=1, value=company)
        c2.font = self._meta_font
        c2.fill = _META_FILL
        c2.alignment = Alignment(horizontal="left", vertical="center", indent=1)

        ws.merge_cells(start_row=2, start_column=15, end_row=2, end_column=16)
        c3 = ws.cell(row=2, column=15, value="版本")
        c3.font = Font(name=_FONT_NAME, size=10, bold=True, color="1F4E79")
        c3.fill = _META_FILL
        c3.alignment = self._center

        ws.merge_cells(start_row=2, start_column=17, end_row=2, end_column=COL_COUNT)
        c4 = ws.cell(row=2, column=17, value=version)
        c4.font = self._meta_font
        c4.fill = _META_FILL
        c4.alignment = self._left
        ws.row_dimensions[2].height = 20
        ws.row_dimensions[3].height = 8

    def _write_headers(self, ws: Any) -> None:
        row4 = {
            1: "序号",
            2: "零件号",
            3: "零件名称",
            4: "零件简图",
            5: "材质",
            6: "料厚",
            7: "零件重量",
            8: "料片尺寸（mm）",
            10: "可制件数",
            11: "料片式样",
            12: "工艺",
            15: "使用冲压设备吨位",
            16: "模具类型",
            17: "工艺方法",
            18: "自动化",
            19: "备注",
            20: "费用比例",
        }
        row5 = {
            8: "长/卷料宽",
            9: "宽/卷料步距",
            12: "工序名称",
            13: "工序",
            14: "套数",
        }
        merges = [
            (4, 1, 5, 1),
            (4, 2, 5, 2),
            (4, 3, 5, 3),
            (4, 4, 5, 4),
            (4, 5, 5, 5),
            (4, 6, 5, 6),
            (4, 7, 5, 7),
            (4, 8, 4, 9),
            (4, 10, 5, 10),
            (4, 11, 5, 11),
            (4, 12, 4, 14),
            (4, 15, 5, 15),
            (4, 16, 5, 16),
            (4, 17, 5, 17),
            (4, 18, 5, 18),
            (4, 19, 5, 19),
            (4, 20, 5, 20),
        ]
        for r1, c1, r2, c2 in merges:
            if (r1, c1) != (r2, c2):
                ws.merge_cells(start_row=r1, start_column=c1, end_row=r2, end_column=c2)

        for col in range(1, COL_COUNT + 1):
            for row in (4, 5):
                cell = ws.cell(row=row, column=col)
                cell.font = self._header_font
                cell.fill = _HEADER_FILL if row == 4 else _SUB_HEADER_FILL
                cell.alignment = self._center
                cell.border = _THIN
        for col, value in row4.items():
            ws.cell(row=4, column=col, value=value)
        for col, value in row5.items():
            ws.cell(row=5, column=col, value=value)
        ws.row_dimensions[4].height = 22
        ws.row_dimensions[5].height = 22

    def _write_part_block(
        self,
        ws: Any,
        *,
        start_row: int,
        seq_no: int,
        part: StampingPart,
        processes: list[StampingProcess],
        blanks: list[StampingTailorWeldBlank],
        zebra: bool,
        sketch_buffers: list[BytesIO],
    ) -> tuple[int, bool]:
        n_rows = max(len(processes), len(blanks), 1)
        end_row = start_row + n_rows - 1
        fill = _ZEBRA if zebra else None

        for offset in range(n_rows):
            excel_row = start_row + offset
            ws.row_dimensions[excel_row].height = DEFAULT_ROW_HEIGHT
            for col in range(1, COL_COUNT + 1):
                cell = ws.cell(row=excel_row, column=col, value=None)
                cell.font = self._data_font
                cell.border = _THIN
                cell.alignment = self._center
                if fill is not None:
                    cell.fill = fill

        part_cols: tuple[int, ...] = (1, 2, 3, 4, 5, 7, 10, 11, 16, 17, 18, 19)
        if not blanks:
            part_cols = (*part_cols, 6, 8, 9)
        for col in part_cols:
            _merge_if_needed(ws, start_row, end_row, col)

        ws.cell(row=start_row, column=1, value=seq_no).alignment = self._center
        ws.cell(row=start_row, column=2, value=part.part_number).alignment = self._left
        ws.cell(row=start_row, column=3, value=part.part_name or "").alignment = self._left
        ws.cell(row=start_row, column=5, value=part.material or "")
        ws.cell(row=start_row, column=7, value=_num(part.part_weight, Q4)).alignment = self._right
        ws.cell(row=start_row, column=10, value=part.parts_per_sheet)
        ws.cell(row=start_row, column=11, value=part.sheet_type or "")
        ws.cell(row=start_row, column=16, value=part.die_type or "")
        ws.cell(row=start_row, column=17, value=part.process_method or "")
        ws.cell(row=start_row, column=18, value=part.automation or "")
        ws.cell(row=start_row, column=19, value=part.remark or "").alignment = self._left

        if blanks:
            spans = _split_spans(n_rows, len(blanks))
            for blank, (rel_start, rel_end) in zip(blanks, spans, strict=False):
                abs_start = start_row + rel_start
                abs_end = start_row + rel_end
                for col in (6, 8, 9):
                    _merge_if_needed(ws, abs_start, abs_end, col)
                thickness = blank.thickness if blank.thickness is not None else part.thickness
                length = blank.sheet_length if blank.sheet_length is not None else part.sheet_length
                width = blank.sheet_width if blank.sheet_width is not None else part.sheet_width
                ws.cell(row=abs_start, column=6, value=_num(thickness, Q4)).alignment = self._right
                ws.cell(row=abs_start, column=8, value=_num(length, Q2)).alignment = self._right
                ws.cell(row=abs_start, column=9, value=_num(width, Q2)).alignment = self._right
        else:
            ws.cell(row=start_row, column=6, value=_num(part.thickness, Q4)).alignment = self._right
            ws.cell(
                row=start_row, column=8, value=_num(part.sheet_length, Q2)
            ).alignment = self._right
            ws.cell(
                row=start_row, column=9, value=_num(part.sheet_width, Q2)
            ).alignment = self._right

        for offset, process in enumerate(processes):
            excel_row = start_row + offset
            ws.cell(row=excel_row, column=12, value=process.process_seq)
            ws.cell(row=excel_row, column=13, value=process.process_code or "")
            ws.cell(row=excel_row, column=14, value=process.die_sets)
            ws.cell(row=excel_row, column=15, value=process.tonnage)
            ratio_cell = ws.cell(
                row=excel_row,
                column=20,
                value=_num(process.cost_ratio, Q2),
            )
            ratio_cell.alignment = self._right

        has_sketch = self._embed_sketch(
            ws,
            part=part,
            start_row=start_row,
            n_rows=n_rows,
            sketch_buffers=sketch_buffers,
        )
        return n_rows, has_sketch

    def _embed_sketch(
        self,
        ws: Any,
        *,
        part: StampingPart,
        start_row: int,
        n_rows: int,
        sketch_buffers: list[BytesIO],
    ) -> bool:
        """把零件简图锚定到 D 列合并格左上角，按格缩放；缺文件则跳过。"""
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
