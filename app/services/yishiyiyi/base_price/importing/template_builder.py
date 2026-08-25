"""钢材基准价格 Excel 导入模板生成。"""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

CellValue = str | int | None


def build_steel_base_price_template() -> tuple[bytes, str]:
    """生成基准价格样例宽表（表头跨行/跨列合并，对齐发布价实样）。"""
    workbook = Workbook()
    sheet = workbook.worksheets[0]
    sheet.title = "Sheet1"

    header_font = Font(name="微软雅黑", size=9, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    data_font = Font(name="微软雅黑", size=9)
    thin = Border(
        left=Side(style="thin", color="BFBFBF"),
        right=Side(style="thin", color="BFBFBF"),
        top=Side(style="thin", color="BFBFBF"),
        bottom=Side(style="thin", color="BFBFBF"),
    )
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    sheet.merge_cells("A1:N1")
    sheet["A1"] = "密级：内部资料□  外部公开□     发放范围：奇瑞外协冲压厂（模板演示）"

    sheet.merge_cells("D2:N2")
    sheet["D2"] = "外协钢板样例订单(样例月冲焊件原料)一事一议价格"
    sheet["D2"].font = Font(name="微软雅黑", size=12, bold=True)
    sheet["D2"].alignment = center

    sheet.merge_cells("M3:N3")
    sheet["M3"] = "元/吨，不含税"
    sheet["M3"].alignment = center

    # 固定列：跨 R4-R5
    sheet.merge_cells("A4:A5")
    sheet["A4"] = "序号"
    sheet.merge_cells("B4:B5")
    sheet["B4"] = "钢种"
    sheet.merge_cells("C4:D5")
    sheet["C4"] = "牌号"
    sheet.merge_cells("E4:E5")
    sheet["E4"] = "参考规格"

    # 基地名跨两列（R4）
    sheet.merge_cells("F4:G4")
    sheet["F4"] = "芜湖基地"
    sheet.merge_cells("H4:I4")
    sheet["H4"] = "大连基地"
    sheet.merge_cells("J4:K4")
    sheet["J4"] = "青岛基地"
    sheet.merge_cells("L4:M4")
    sheet["L4"] = "鄂尔多斯基地"

    # R5 子列
    sheet["F5"] = "钢厂"
    sheet["G5"] = "到厂原卷承兑价格"
    sheet["H5"] = "钢厂"
    sheet["I5"] = "到厂原卷承兑价格"
    sheet["J5"] = "钢厂"
    sheet["K5"] = "到厂原卷承兑价格"
    sheet["L5"] = "钢厂"
    sheet["M5"] = "到厂原卷承兑价格"

    for row in (4, 5):
        for col in range(1, 14):
            cell = sheet.cell(row=row, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center
            cell.border = thin

    samples: list[tuple[int, str, str, str, str, int, str, int, str, int, str, int]] = [
        (1, "镀锌", "DC51D+Z", "1.0*1250", "VAMA", 4123, "VAMA", 4236, "山钢", 4113, "VAMA", 4291),
        (2, "镀锌", "DC53D+Z", "1.0*1250", "本钢", 4521, "本钢", 4465, "山钢", 4480, "山钢", 4665),
        (3, "冷轧", "DC04", "0.8*1250", "宝钢", 3980, "宝钢", 4050, "首钢", 4010, "宝钢", 4120),
        (4, "冷轧", "HC340LA", "1.2*1500", "马钢", 4210, "马钢", 4280, "唐钢", 4195, "马钢", 4350),
    ]
    for row_idx, sample in enumerate(samples, start=6):
        # 牌号跨 C:D（对齐实样）
        sheet.merge_cells(
            start_row=row_idx,
            start_column=3,
            end_row=row_idx,
            end_column=4,
        )
        values: list[tuple[int, CellValue]] = [
            (1, sample[0]),
            (2, sample[1]),
            (3, sample[2]),
            (5, sample[3]),
            (6, sample[4]),
            (7, sample[5]),
            (8, sample[6]),
            (9, sample[7]),
            (10, sample[8]),
            (11, sample[9]),
            (12, sample[10]),
            (13, sample[11]),
        ]
        for col, cell_value in values:
            cell = sheet.cell(row=row_idx, column=col, value=cell_value)
            cell.font = data_font
            cell.alignment = center
        for col in range(1, 14):
            sheet.cell(row=row_idx, column=col).border = thin

    for idx in range(1, 14):
        sheet.column_dimensions[get_column_letter(idx)].width = 12
    sheet.column_dimensions["C"].width = 10
    sheet.column_dimensions["D"].width = 10
    sheet.column_dimensions["E"].width = 12
    sheet.row_dimensions[4].height = 22
    sheet.row_dimensions[5].height = 32
    sheet.freeze_panes = "A6"

    note = workbook.create_sheet("填写说明")
    _write_notes(
        note,
        [
            "正式文件为奇瑞发布的「发布价格及中标钢厂」Excel（外协钢板订单一事一议价格）。",
            "序号/钢种/牌号/规格列跨第4-5行合并；基地名跨两列；牌号数据行可跨 C:D。",
            "第 5 行为「钢厂 / 到厂原卷承兑价格」子列；数据从第 6 行起。",
            "价格单位：元/吨，不含税；钢厂列不得填数字（防列错位）。",
            "上传页须手工填写生效年度与月份。",
        ],
    )

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue(), "基准价格导入模板.xlsx"


def _write_notes(sheet: Worksheet, lines: list[str]) -> None:
    sheet["A1"] = "填写说明"
    sheet["A1"].font = Font(name="微软雅黑", size=12, bold=True, color="C00000")
    for idx, line in enumerate(lines, start=3):
        sheet.cell(row=idx, column=1, value=f"{idx - 2}. {line}")
        sheet.cell(row=idx, column=1).font = Font(name="微软雅黑", size=10)
        sheet.cell(row=idx, column=1).alignment = Alignment(wrap_text=True, vertical="center")
        sheet.row_dimensions[idx].height = 22
    sheet.column_dimensions["A"].width = 96
