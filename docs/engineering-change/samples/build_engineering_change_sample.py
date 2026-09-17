"""工程变更样表：封皮 + 三张业务表从日常三个导入模板原样拷贝，再填本例数据。"""

from __future__ import annotations

import sys
from copy import copy
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.worksheet import Worksheet

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from app.services.bom.bom_template_builder import build_bom_material_template  # noqa: E402
from app.services.stamping.die.template_builder import build_die_layout_template  # noqa: E402
from app.services.stamping.upload.template_builder import (  # noqa: E402
    build_stamping_process_template,
)

OUT = Path(__file__).with_name("engineering-change-t13j-3086ab.xlsx")

_THIN = Border(
    left=Side(style="thin", color="BFBFBF"),
    right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"),
    bottom=Side(style="thin", color="BFBFBF"),
)
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_DATA_FONT = Font(name="微软雅黑", size=9)


def _copy_sheet(source: Worksheet, dest_wb: Workbook, title: str) -> Worksheet:
    dest = dest_wb.create_sheet(title)
    for row in source.iter_rows():
        for cell in row:
            cloned = dest.cell(cell.row, cell.column, cell.value)
            if cell.has_style:
                cloned.font = copy(cell.font)
                cloned.border = copy(cell.border)
                cloned.fill = copy(cell.fill)
                cloned.number_format = cell.number_format
                cloned.protection = copy(cell.protection)
                cloned.alignment = copy(cell.alignment)
    for merged in source.merged_cells.ranges:
        dest.merge_cells(str(merged))
    for letter, dim in source.column_dimensions.items():
        dest.column_dimensions[letter].width = dim.width
    for index, dim in source.row_dimensions.items():
        dest.row_dimensions[index].height = dim.height
    dest.freeze_panes = source.freeze_panes
    dest.sheet_view.zoomScale = source.sheet_view.zoomScale or 100
    dest.print_title_rows = source.print_title_rows
    dest.print_area = source.print_area
    return dest


def _load_template(content: bytes):
    return load_workbook(BytesIO(content))


def _unmerge_in_rows(sheet: Worksheet, min_row: int, max_row: int) -> None:
    ranges = [
        str(item)
        for item in sheet.merged_cells.ranges
        if item.min_row >= min_row and item.max_row <= max_row
    ]
    for item in ranges:
        sheet.unmerge_cells(item)


def _clear_row_range(sheet: Worksheet, start_row: int, end_row: int, max_col: int) -> None:
    _unmerge_in_rows(sheet, start_row, end_row)
    for row in range(start_row, end_row + 1):
        for col in range(1, max_col + 1):
            sheet.cell(row, col).value = None


def _write_cover(sheet: Worksheet) -> None:
    title = Font(name="微软雅黑", size=14, bold=True)
    label = Font(name="微软雅黑", size=10)
    head = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="4472C4")
    sheet["A1"] = "工程变更（封皮）"
    sheet["A1"].font = title
    sheet.merge_cells("A1:J1")
    sheet["A2"] = (
        "后面三张表和日常导入模板相同。"
        "基地 芜湖，顾客 奇瑞公司。"
        "先写变更类型和原来的交货总成，再写这一次动到的零件。"
        "总成名称变更前后相同，只写一列。本行是总成改图：零件两列与零件名称空。"
        "材料清单只写变化的行，没变的零件不要抄。"
        "材料清单序号系统按变更前总成带出，人不用填。"
    )
    sheet["A2"].font = Font(name="微软雅黑", size=9, color="666666")
    sheet["A2"].alignment = Alignment(wrap_text=True, vertical="center")
    sheet.merge_cells("A2:J2")
    sheet.row_dimensions[2].height = 64
    headers = (
        "项目",
        "生效年月",
        "变更类型",
        "变更前总成",
        "变更后总成",
        "总成名称",
        "零件层级",
        "变更前零件",
        "变更后零件",
        "零件名称",
    )
    for col, header in enumerate(headers, start=1):
        cell = sheet.cell(4, col, header)
        cell.font = head
        cell.fill = fill
        cell.border = _THIN
        cell.alignment = _CENTER
    values = (
        "T13J",
        "2026年08月",
        "改图",
        "551003086AA",
        "551003086AB",
        "右前门上铰链加强板总成",
        "总成",
        "",
        "",
        "",
    )
    for col, value in enumerate(values, start=1):
        cell = sheet.cell(5, col, value)
        cell.font = label
        cell.border = _THIN
        cell.alignment = _CENTER
    sheet.row_dimensions[5].height = 28
    widths = (12, 14, 12, 22, 22, 28, 10, 22, 22, 28)
    for col, width in enumerate(widths, start=1):
        sheet.column_dimensions[chr(64 + col)].width = width
    sheet.freeze_panes = "A5"


def _fill_bom_change_tree(sheet: Worksheet) -> None:
    sheet["A1"] = "T13J项目产品材料清单"
    sheet["A2"] = (
        "编制部门： 技术中心                    "
        "编制日期：2026-08-01  版本： EC-202608  编号：EC-T13J-3086AB"
    )
    sheet["A3"] = "项目代号：  T13J"
    sheet["I3"] = "产品类别：  车身件"
    sheet["N3"] = "顾客名称：  奇瑞公司"
    sheet["P3"] = "阶段标识： D"
    sheet["R3"] = "■批量生产清单"
    sheet["V3"] = "修订日期：2026-08-01"

    _clear_row_range(sheet, 5, 20, 23)
    for row in range(5, 8):
        for col in range(1, 24):
            cell = sheet.cell(row, col)
            cell.font = _DATA_FONT
            cell.border = _THIN
            cell.alignment = _CENTER
        sheet.row_dimensions[row].height = 22

    def merge_vertical(col: int, start: int, end: int) -> None:
        if end > start:
            sheet.merge_cells(start_row=start, start_column=col, end_row=end, end_column=col)

    for col in range(1, 8):
        merge_vertical(col, 5, 7)
    for col in range(8, 13):
        merge_vertical(col, 6, 7)

    sheet.cell(5, 1, 5)
    sheet.cell(5, 2, "ACA674")
    sheet.cell(5, 3, "551003086AB")
    sheet.cell(5, 4, "右前门上铰链加强板总成")
    sheet.cell(5, 6, 1)
    sheet.cell(5, 7, "CO2焊 点焊")
    sheet.cell(5, 8, "ACA674001")
    sheet.cell(5, 9, "551003096AA")
    sheet.cell(5, 10, "右前门上铰链加强板")
    sheet.cell(5, 11, 1)
    sheet.cell(5, 12, "/")
    sheet.cell(5, 13, "/")
    sheet.cell(5, 14, "/")
    sheet.cell(5, 15, "/")
    sheet.cell(5, 17, 1)
    sheet.cell(5, 18, "HC180YD+Z")
    sheet.cell(5, 19, "T=1.2")
    sheet.cell(5, 20, "烟台海众")
    sheet.cell(5, 21, 0.85)
    sheet.cell(5, 22, "是")
    sheet.cell(5, 23, "一级冲压未改图")

    sheet.cell(6, 8, "ACA333N01")
    sheet.cell(6, 9, "551001137AB")
    sheet.cell(6, 10, "左后门上铰链安装板总成")
    sheet.cell(6, 11, 1)
    sheet.cell(6, 12, "/")
    sheet.cell(6, 13, "/")
    sheet.cell(6, 14, "551001133AB")
    sheet.cell(6, 15, "左后门上铰链安装板")
    sheet.cell(6, 17, 1)
    sheet.cell(6, 18, "DC01")
    sheet.cell(6, 19, "T=1.5")
    sheet.cell(6, 20, "安徽振华")
    sheet.cell(6, 21, 0.62)
    sheet.cell(6, 22, "是")
    sheet.cell(6, 23, "分总成换AB")

    sheet.cell(7, 13, "/")
    sheet.cell(7, 14, "QR36410")
    sheet.cell(7, 15, "焊接方螺母")
    sheet.cell(7, 17, 2)
    sheet.cell(7, 19, "M6")
    sheet.cell(7, 21, 0.008)
    sheet.cell(7, 22, "/")
    sheet.cell(7, 23, "标准件未改图")


def _strip_process_sample(sheet: Worksheet) -> None:
    sheet["D2"] = "T13J项目冲压工艺确认表-工程变更"
    max_row = sheet.max_row or 6
    _clear_row_range(sheet, 7, max(max_row, 7), 20)


def _strip_die_sample(sheet: Worksheet) -> None:
    note_row = 6
    for row in range(6, (sheet.max_row or 6) + 1):
        text = str(sheet.cell(row, 1).value or "")
        if "模具费分摊说明" in text:
            note_row = row
            break
    _clear_row_range(sheet, 6, note_row - 1, 30)
    for col in range(1, 31):
        cell = sheet.cell(6, col)
        cell.border = Border(
            left=Side(style="thin", color="000000"),
            right=Side(style="thin", color="000000"),
            top=Side(style="thin", color="000000"),
            bottom=Side(style="thin", color="000000"),
        )
        cell.font = Font(name="宋体", size=12)
        cell.alignment = _CENTER


def main() -> None:
    bom_wb = _load_template(build_bom_material_template()[0])
    process_wb = _load_template(build_stamping_process_template()[0])
    die_wb = _load_template(build_die_layout_template()[0])

    combined = Workbook()
    cover = combined.active
    if cover is None:
        cover = combined.create_sheet("封皮")
    cover.title = "封皮"
    _write_cover(cover)

    bom_sheet = _copy_sheet(bom_wb["车身件材料清单"], combined, "车身件材料清单")
    _fill_bom_change_tree(bom_sheet)
    _copy_sheet(bom_wb["填写说明"], combined, "材料清单填写说明")

    process_sheet = _copy_sheet(process_wb["冲压工艺确认表"], combined, "冲压工艺确认表")
    _strip_process_sample(process_sheet)
    _copy_sheet(process_wb["填写说明"], combined, "工艺确认填写说明")

    die_sheet = _copy_sheet(die_wb["零件汇总"], combined, "零件汇总")
    _strip_die_sample(die_sheet)

    temp_out = OUT.with_suffix(".building.xlsx")
    combined.save(temp_out)
    try:
        temp_out.replace(OUT)
    except OSError:
        print(f"目标文件被占用，已写出: {temp_out}")
        return
    print(OUT)


if __name__ == "__main__":
    main()
