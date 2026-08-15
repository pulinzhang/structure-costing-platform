"""中标钢厂厚度价格一览 Excel 生成。"""

from __future__ import annotations

import logging
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app.schemas.vo.winning_thickness_vo import WinningThicknessRowVO

logger = logging.getLogger("service.winning_thickness.export.excel")

_WEAK_COLS = frozenset({1, 9, 10})
_PRICE_COLS = frozenset({5, 6, 7, 8})

_HEADERS = [
    "基地/钢种",
    "牌号",
    "钢厂",
    "厚度范围",
    "基准价(元/吨)",
    "加减价(元/吨)",
    "加工费(元/吨)",
    "最终价(元/吨)",
    "基价溯源",
    "厚度溯源",
]

_COLUMN_WIDTHS = [18, 14, 12, 18, 14, 14, 14, 14, 36, 36]


class WinningThicknessExporter:
    """将一览行写成 xlsx。"""

    @staticmethod
    def _format_location_category(location: str | None, category_name: str | None) -> str:
        loc = (location or "").strip()
        cat = (category_name or "").strip()
        if loc and cat:
            return f"{loc} · {cat}"
        return loc or cat or ""

    @staticmethod
    def _format_base_trace(row: WinningThicknessRowVO) -> str:
        parts = []
        if row.base_price_id is not None:
            parts.append(f"ID:{row.base_price_id}")
        if row.base_excel_filename:
            parts.append(row.base_excel_filename)
        if row.base_sheet_name:
            parts.append(row.base_sheet_name)
        if row.base_excel_row is not None:
            parts.append(f"R{row.base_excel_row}")
        if row.base_excel_col is not None:
            parts.append(f"C{row.base_excel_col}")
        return " · ".join(parts)

    @staticmethod
    def _format_thickness_trace(row: WinningThicknessRowVO) -> str:
        parts = []
        if row.thickness_policy_id is not None:
            parts.append(f"P:{row.thickness_policy_id}")
        if row.thickness_ladder_item_id is not None:
            parts.append(f"L:{row.thickness_ladder_item_id}")
        if row.thickness_excel_filename:
            parts.append(row.thickness_excel_filename)
        if row.thickness_excel_row is not None:
            parts.append(f"R{row.thickness_excel_row}")
        if row.thickness_excel_col is not None:
            parts.append(f"C{row.thickness_excel_col}")
        return " · ".join(parts)

    def generate(
        self,
        rows: list[WinningThicknessRowVO],
        *,
        year: int,
        month: int,
        location: str,
    ) -> tuple[bytes, str]:
        wb = Workbook()
        ws = wb.active
        ws.title = "厚度价格一览"

        header_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="4472C4", end_color="4472C4", fill_type="solid"
        )
        weak_header_fill = PatternFill(
            start_color="8FAADC", end_color="8FAADC", fill_type="solid"
        )
        header_alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True
        )

        data_font = Font(name="微软雅黑", size=10, color="000000")
        weak_font = Font(name="微软雅黑", size=8, color="808080")
        data_left = Alignment(horizontal="left", vertical="center")
        data_right = Alignment(horizontal="right", vertical="center")

        thin_border = Border(
            left=Side(style="thin", color="BFBFBF"),
            right=Side(style="thin", color="BFBFBF"),
            top=Side(style="thin", color="BFBFBF"),
            bottom=Side(style="thin", color="BFBFBF"),
        )

        ws.append(_HEADERS)
        ws.row_dimensions[1].height = 28
        for col_idx in range(1, len(_HEADERS) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = weak_header_fill if col_idx in _WEAK_COLS else header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        for row_idx, row in enumerate(rows, start=2):
            values = [
                self._format_location_category(row.location, row.category_name),
                row.grade,
                row.steel_mill,
                row.thickness_range,
                row.base_price,
                row.thickness_adjustment,
                row.processing_fee,
                row.final_price,
                self._format_base_trace(row),
                self._format_thickness_trace(row),
            ]
            ws.append(values)
            fill = PatternFill(
                start_color="F2F2F2" if row_idx % 2 == 0 else "FFFFFF",
                end_color="F2F2F2" if row_idx % 2 == 0 else "FFFFFF",
                fill_type="solid",
            )
            for col_idx in range(1, len(values) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.border = thin_border
                cell.fill = fill
                cell.font = weak_font if col_idx in _WEAK_COLS else data_font
                cell.alignment = data_right if col_idx in _PRICE_COLS else data_left

        for col_idx, width in enumerate(_COLUMN_WIDTHS, start=1):
            letter = ws.cell(row=1, column=col_idx).column_letter
            ws.column_dimensions[letter].width = width

        ws.freeze_panes = "A2"

        filename = f"中标钢厂厚度价格一览表_{year}年_{month}月_{location}.xlsx"
        output = BytesIO()
        wb.save(output)
        logger.info(
            "导出中标钢厂厚度价格一览表完成: filename=%s rows=%d",
            filename,
            len(rows),
        )
        return output.getvalue(), filename
