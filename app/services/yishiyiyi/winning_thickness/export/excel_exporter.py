"""中标钢厂厚度价格一览 Excel 生成（编排入口）。"""

from __future__ import annotations

import logging
from io import BytesIO

from openpyxl import Workbook

from app.common.timezone import now
from app.schemas.vo.winning_thickness_vo import WinningThicknessRowVO
from app.services.yishiyiyi.winning_thickness.export.calc_sheet import write_calc_sheet
from app.services.yishiyiyi.winning_thickness.export.example_sheet import write_example_sheet
from app.services.yishiyiyi.winning_thickness.export.letterhead import WorkbookMeta
from app.services.yishiyiyi.winning_thickness.export.overview_sheet import write_overview_sheet
from app.services.yishiyiyi.winning_thickness.export.values import (
    CALC_SHEET_SUFFIX,
    EXAMPLE_SHEET_SUFFIX,
    OVERVIEW_SHEET_SUFFIX,
    build_filename,
    scoped_sheet_name,
)

logger = logging.getLogger("service.winning_thickness.export.excel")


class WinningThicknessExporter:
    """将一览行写成 xlsx（阅读页 + 计算页 + 示例页）。"""

    def generate(
        self,
        rows: list[WinningThicknessRowVO],
        *,
        year: int,
        month: int,
        location: str,
    ) -> tuple[bytes, str]:
        meta = WorkbookMeta(
            year=year,
            month=month,
            location=location,
            row_count=len(rows),
            exported_at=now(),
        )
        wb = Workbook()
        overview = wb.worksheets[0]
        overview.title = scoped_sheet_name(
            year=year,
            month=month,
            location=location,
            suffix=OVERVIEW_SHEET_SUFFIX,
        )
        write_overview_sheet(overview, rows, meta)

        calc_sheet = wb.create_sheet(
            scoped_sheet_name(
                year=year,
                month=month,
                location=location,
                suffix=CALC_SHEET_SUFFIX,
            )
        )
        write_calc_sheet(calc_sheet, rows, meta)

        example_sheet = wb.create_sheet(
            scoped_sheet_name(
                year=year,
                month=month,
                location=location,
                suffix=EXAMPLE_SHEET_SUFFIX,
            )
        )
        write_example_sheet(example_sheet, rows, meta)

        filename = build_filename(year=year, month=month, location=location)
        output = BytesIO()
        wb.save(output)
        logger.info(
            "导出中标钢厂厚度价格一览表完成: filename=%s rows=%d",
            filename,
            len(rows),
        )
        return output.getvalue(), filename
