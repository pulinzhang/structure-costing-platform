"""冲压模具布点导入模板。"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.worksheet import Worksheet


def _active_worksheet(workbook: Workbook, title: str) -> Worksheet:
    sheet = workbook.active
    if not isinstance(sheet, Worksheet):
        sheet = workbook.create_sheet(title)
    sheet.title = title
    return sheet


def build_die_layout_template() -> tuple[bytes, str]:
    workbook = Workbook()
    sheet = _active_worksheet(workbook, "零件汇总")
    _write_headers(sheet)
    _write_sample(sheet)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue(), "冲压模具布点导入模板.xlsx"


def _write_headers(sheet: Worksheet) -> None:
    fill = PatternFill("solid", fgColor="1E1E1E")
    font = Font(color="FFFFFF", bold=True, size=9)
    sheet.merge_cells("B3:G3")
    sheet["B3"] = "产品信息"
    sheet["A3"] = "序号"
    sheet["H3"] = "工艺清单"
    sheet["A4"] = ""
    headers_r4 = {
        "B": "零件号",
        "C": "零件名称",
        "D": "简图(不导入)",
        "E": "材质",
        "F": "料厚（mm）",
        "G": "净重（kg）",
        "H": "预估板料尺寸（mm）",
        "J": "板料形状",
        "K": "可制件数",
        "L": "预估单件材料消耗（KG）",
        "M": "预估单件材料利用率",
        "N": "预估工艺",
        "Q": "预估模具尺寸（mm*mm*mm）",
        "T": "掏空系数",
        "U": "预估重量（T）",
        "V": "预估重量小计（T）",
        "W": "使用设备吨位（T）",
        "X": "模具类型",
        "Y": "模具方式",
        "Z": "生产方式",
        "AA": "是否需要端拾器",
        "AB": "零件等级",
        "AC": "备注",
    }
    for col, text in headers_r4.items():
        sheet[f"{col}4"] = text
    sheet["H5"] = "长"
    sheet["I5"] = "宽"
    sheet["N5"] = "工序名称"
    sheet["O5"] = "工序"
    sheet["P5"] = "套数"
    sheet["Q5"] = "长度"
    sheet["R5"] = "宽度"
    sheet["S5"] = "高度"
    for cell in sheet["3:5"]:
        for item in cell:
            if item.value:
                item.font = font
                item.fill = fill
                item.alignment = Alignment(wrap_text=True, vertical="center")


def _write_sample(sheet: Worksheet) -> None:
    sheet["A6"] = 1
    sheet["B6"] = "502007709AA"
    sheet["C6"] = "样例零件"
    sheet["E6"] = "DC04"
    sheet["F6"] = 0.65
    sheet["G6"] = 0.16
    sheet["H6"] = 880
    sheet["I6"] = 850
    sheet["J6"] = "板料"
    sheet["K6"] = 1
    sheet["L6"] = 0.5
    sheet["M6"] = 0.65
    sheet["N6"] = "OP10"
    sheet["O6"] = "BL"
    sheet["P6"] = 1
    sheet["Q6"] = 650
    sheet["R6"] = 400
    sheet["S6"] = 320
    sheet["T6"] = 0.65
    sheet["U6"] = 0.42
    sheet["V6"] = 0.42
    sheet["W6"] = 160
    sheet["X6"] = "钢板模"
    sheet["Y6"] = "单干"
    sheet["Z6"] = "手工线"
    sheet["AB6"] = "C"
    sheet["AC6"] = "模板样例，请按布点清单填写"
