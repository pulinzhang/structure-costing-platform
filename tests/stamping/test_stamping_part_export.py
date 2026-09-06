"""冲压工艺确认表导出含是否摆剪。"""

from openpyxl import Workbook

from app.services.stamping.stamping_part_export_service import (
    COL_COUNT,
    WIDTHS,
    StampingPartExportService,
)


def test_process_confirm_export_headers_include_swing_shear() -> None:
    assert COL_COUNT == 27
    assert len(WIDTHS) == COL_COUNT
    workbook = Workbook()
    sheet = workbook.active
    StampingPartExportService()._write_headers(sheet)
    assert sheet.cell(4, 15).value == "是否利废"
    assert sheet.cell(4, 16).value == "利用哪类废料"
    assert sheet.cell(4, 17).value == "是否摆剪"
    assert sheet.cell(4, 18).value == "工艺"
    assert sheet.cell(4, 27).value == "费用比例"
