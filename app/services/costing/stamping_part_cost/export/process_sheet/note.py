"""附录工作表「冲压核价口径」。"""

from __future__ import annotations

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill

from app.common.excel_workbook import resolve_worksheet


def write_formula_note_sheet(
    workbook: Workbook,
    *,
    density_text: str,
    loss_rate_text: str,
    loss_permille_text: str,
    recovery_text: str,
    recovery_percent_text: str,
    thin: Border,
    center: Alignment,
    left: Alignment,
    meta_font: Font,
) -> None:
    note = resolve_worksheet(workbook, "冲压核价口径")
    note_font_title = Font(name="微软雅黑", size=12, bold=True, color="1F1F1F")
    note_font = Font(name="微软雅黑", size=10, color="333333")
    note_header = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    note_header_fill = PatternFill("solid", fgColor="455A64")
    note["A1"] = "冲压零件核价口径定义"
    note["A1"].font = note_font_title
    note.merge_cells("A1:C1")
    note.row_dimensions[1].height = 24
    # 用户看到的是纯中文+符号，没有下划线变量名
    note["A2"] = (
        f"本批次参数：钢材密度 ρ（柔 Rho）={density_text} g/cm³；"
        f"材料损耗率 λ（拉姆达 Lambda）={loss_rate_text}（{loss_permille_text}‰）；"
        f"废料回收率 η（伊塔 Eta）={recovery_text}（{recovery_percent_text}%）"
    )
    note["A2"].font = meta_font
    note.merge_cells("A2:C2")

    note_headers = ("符号", "定义", "计算关系 / 单位")
    for col, text in enumerate(note_headers, start=1):
        cell = note.cell(4, col, text)
        cell.font = note_header
        cell.fill = note_header_fill
        cell.alignment = center
        cell.border = thin

    note_rows = [
        ("B", "总成供货号", "同基地 BOM 沿 parent 上溯至 L0；多总成逗号分隔"),
        ("C", "零件号", "本行核算零件号"),
        ("D", "短码", "零件号数字体末四位"),
        ("L, W, T", "板料长、宽(步距)、料厚", "mm；拼焊件每个子片单独一行"),
        ("n", "可制件数", "件/板；拼焊件按子片行填写"),
        ("ρ_steel", "钢材密度", f"{density_text} g/cm³"),
        ("1,000,000", "量纲换算系数", "mm³·(g/cm³) → kg"),
        (
            "N",
            "预估单件材料消耗",
            "普通件 / 拼焊子片行：=K×L×H×ρ/1e6/M；" "总成消耗 = SUM(各子片 N)",
        ),
        ("I", "零件净重", "kg；拼焊件为焊后总成净重，跨子片行合并"),
        ("P", "废料重量", "普通件 P=N−I；拼焊件 P=SUM(N)−I（合并格）"),
        (
            "Q",
            "钢板单价",
            "元/kg（吨价÷1000，含本月摆剪加价）；拼焊件各子片一行各自单价",
        ),
        ("R", "废料单价", "元/kg（吨价÷1000）"),
        ("λ", "材料损耗率", f"{loss_rate_text}（{loss_permille_text}‰）"),
        ("η", "废料回收率", f"{recovery_text}（{recovery_percent_text}%）"),
        ("①", "钢材采购额", "普通件 N×Q×(1+λ)；拼焊件 Σ(Ni×Qi×(1+λ))"),
        ("②", "损耗废料扣除", "N×λ×η×R（拼焊件与 Σ Ni×λ×η×R 等价）"),
        ("③", "边角废料扣除", "P × η × R（总成一次）"),
        (
            "S",
            "原材料成本",
            "普通件：=N×Q×(1+λ)−N×λ×η×R−P×η×R；"
            "拼焊件：=Σ(Ni×Qi×(1+λ))−SUM(N)×λ×η×R−P×η×R（引用各子片行）",
        ),
        ("T", "加工费", "元/件；取自加工费核算结果（拼焊父件一行）；0 或空则单元格留空"),
        ("U", "模具费", "元/件；取自年度模具费最终价；无档案或 0 则单元格留空"),
        ("V", "检具费", "元/件；检具费（万元）÷ 分摊万台；无生效档案或 0 则单元格留空"),
        ("W", "直接成本", "S + T + U + V；合计为 0 则单元格留空"),
        ("X", "仓储+包装", "直接成本 × 仓储+包装管理费用率"),
        ("Y", "管理费", "直接成本 × 管理费率"),
        ("Z", "财务费", "直接成本 × 财务费率"),
        ("AA", "税前利润", "直接成本 × 税前利润率"),
        (
            "AB",
            "最终价",
            "直接成本 + 仓储包装费 + 管理费 + 财务费 + 税前利润"
            "（计算时按系统设置费率落库；导出列为公式）",
        ),
        (
            "AC~AH",
            "溯源（弱化）",
            "按文件/表/行定位核对；钢材含基价·厚度·宽度·锌层；"
            "拼焊件可含多条钢材价；废料为基地年月净价；"
            "加工费为工艺文件+工序依据。单元格可手工补填。",
        ),
        (
            "AI~AM",
            "关联ID（弱化）",
            "钢材价ID / 废料价ID / 加工费ID / 模具费ID / 检具费ID；" "拼焊件钢材价ID 按子片分行。",
        ),
        ("AN~AO", "利废", "是否从废料里出成品；利用哪类废料取板料式样扫描结果"),
        ("AP~AQ", "摆剪", "工序含「摆剪」则为是；加价为快照元/吨，已计入 Q"),
    ]
    for idx, (symbol, name, desc) in enumerate(note_rows, start=5):
        note.cell(idx, 1, symbol).font = note_font
        note.cell(idx, 2, name).font = note_font
        note.cell(idx, 3, desc).font = note_font
        for col in range(1, 4):
            note.cell(idx, col).border = thin
            note.cell(idx, col).alignment = left if col > 1 else center

    note.column_dimensions["A"].width = 14
    note.column_dimensions["B"].width = 18
    note.column_dimensions["C"].width = 52
