"""冲压工艺确认表导出含短码与是否摆剪。"""

from types import SimpleNamespace

from openpyxl import Workbook

from app.services.stamping.stamping_part_export_service import (
    COL_COUNT,
    DATA_START_ROW,
    SHORT_CODE_COL,
    WIDTHS,
    StampingPartExportService,
)


def test_process_confirm_export_headers_include_short_code_and_swing_shear() -> None:
    assert COL_COUNT == 28
    assert len(WIDTHS) == COL_COUNT
    workbook = Workbook()
    sheet = workbook.active
    StampingPartExportService()._write_headers(sheet)
    assert sheet.cell(4, 2).value == "零件号"
    assert sheet.cell(4, 3).value == "短码"
    assert sheet.cell(4, 4).value == "零件名称"
    assert sheet.cell(4, 16).value == "是否利废"
    assert sheet.cell(4, 17).value == "利用哪类废料"
    assert sheet.cell(4, 18).value == "是否摆剪"
    assert sheet.cell(4, 19).value == "工艺"
    assert sheet.cell(4, 28).value == "费用比例"


def test_process_confirm_export_writes_last_four_digit_short_code() -> None:
    workbook = Workbook()
    sheet = workbook.active
    part = SimpleNamespace(
        part_number="552000656AA",
        part_name="后背门左铰链加强板",
        stamping_supplier="烟台海众汽车零部件有限公司",
        vehicle_model="T28",
        version="V3",
        location="青岛",
        material="HC340/590DPD+Z",
        part_weight=None,
        parts_per_sheet=4,
        sheet_type="条料",
        is_offal_nested=False,
        offal_source=None,
        has_swing_shear=False,
        die_type="铸造模",
        process_method="双槽",
        automation="手工线",
        remark=None,
        thickness=None,
        sheet_length=None,
        sheet_width=None,
    )
    process = SimpleNamespace(
        process_seq="OP05",
        process_code="BL",
        die_sets=1,
        die_number=None,
        tonnage=400,
        cost_ratio=None,
    )
    StampingPartExportService()._write_part_block(
        sheet,
        start_row=DATA_START_ROW,
        seq_no=1,
        part=part,
        processes=[process],
        blanks=[],
        zebra=False,
        sketch_buffers=[],
    )
    assert sheet.cell(DATA_START_ROW, SHORT_CODE_COL).value == "0656"
