"""写入「冲压核价结果」主表 + 调用附录口径表。

改列布局看 columns.py；改单元格公式看 cells.py；改附录说明看 note.py。
"""

from __future__ import annotations

import logging

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sqlalchemy.orm import Session

from app.common.excel_workbook import resolve_worksheet
from app.common.export_watermark import workbook_to_xlsx_bytes
from app.common.measures import PERCENT, PERMILLE
from app.models.costing import StampingPartCost
from app.repositories.bom.bom.node import BomNodeRepository
from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.stamping.process_fee.repository import (
    StampingProcessFeeRepository,
)
from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.stamping_part_cost.export.formatters import formula_number
from app.services.costing.stamping_part_cost.export.process_sheet.columns import (
    _FEE_RATE_COLS,
    _ID_COLS,
    _PROCESS_COL_LETTERS,
    _SCOPE_WEAK_COLS,
    _TRACE_COLS,
    PROCESS_SHEET_HEADERS,
)
from app.services.costing.stamping_part_cost.export.process_sheet.filename import (
    build_process_sheet_filename,
)
from app.services.costing.stamping_part_cost.export.process_sheet.note import (
    write_formula_note_sheet,
)
from app.services.costing.stamping_part_cost.export.process_sheet.rows import (
    write_process_data_rows,
)
from app.services.costing.stamping_part_cost.helpers import to_decimal
from app.services.settings.system.service import SettingsService

logger = logging.getLogger("service.stamping_part_cost_export")


def write_process_sheet_to_workbook(
    workbook: Workbook,
    db: Session,
    rows: list[StampingPartCost],
    *,
    bom_snapshot_repo: BomSnapshotRepository,
    bom_node_repo: BomNodeRepository,
    steel_price_repo: SteelPriceRepository,
    scrap_price_repo: StampingScrapPriceRepository,
    process_fee_repo: StampingProcessFeeRepository,
    sheet_title: str = "冲压核价结果",
) -> tuple[str, int]:
    """
    将工艺清单口径核价结果写入已有 Workbook（不 save）。
    返回 (主表 sheet 名, 主表零件行数近似用 rows 长度)。
    """
    sheet = resolve_worksheet(workbook, sheet_title)

    last_col = len(_PROCESS_COL_LETTERS)
    last_col_letter = _PROCESS_COL_LETTERS[-1]
    trace_cols = _TRACE_COLS
    id_cols = _ID_COLS
    fee_rate_cols = _FEE_RATE_COLS

    settings_service = SettingsService()
    warehouse_packaging_rate = settings_service.get_finished_warehouse_packaging_rate(db)
    management_rate = settings_service.get_finished_management_rate(db)
    finance_rate = settings_service.get_finished_finance_rate(db)
    pretax_profit_rate = settings_service.get_finished_pretax_profit_rate(db)

    # —— 样式 ——
    thin = Border(
        left=Side(style="thin", color="B0B0B0"),
        right=Side(style="thin", color="B0B0B0"),
        top=Side(style="thin", color="B0B0B0"),
        bottom=Side(style="thin", color="B0B0B0"),
    )
    title_font = Font(name="微软雅黑", size=14, bold=True, color="1F1F1F")
    meta_font = Font(name="微软雅黑", size=9, color="666666")
    group_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    header_font = Font(name="微软雅黑", size=9, bold=True, color="1F1F1F")
    weak_header_font = Font(name="微软雅黑", size=8, bold=True, color="757575")
    data_font = Font(name="微软雅黑", size=9, color="000000")
    weak_data_font = Font(name="微软雅黑", size=8, color="9E9E9E")
    fee_rate_font = Font(name="微软雅黑", size=8, color="757575")
    accent_font = Font(name="微软雅黑", size=9, bold=True, color="C62828")

    fill_title = PatternFill("solid", fgColor="F5F5F5")
    fill_group_id = PatternFill("solid", fgColor="424242")
    fill_group_product = PatternFill("solid", fgColor="455A64")
    fill_group_process = PatternFill("solid", fgColor="1565C0")
    fill_group_fee = PatternFill("solid", fgColor="2E7D32")
    fill_group_fee_rate = PatternFill("solid", fgColor="607D8B")
    fill_group_final = PatternFill("solid", fgColor="C62828")
    fill_group_trace = PatternFill("solid", fgColor="78909C")
    fill_header = PatternFill("solid", fgColor="ECEFF1")
    fill_header_trace = PatternFill("solid", fgColor="ECEFF1")
    fill_header_fee_rate = PatternFill("solid", fgColor="ECEFF1")
    fill_zebra = PatternFill("solid", fgColor="FAFAFA")
    fill_zebra_trace = PatternFill("solid", fgColor="F5F5F5")
    fill_fee_rate = PatternFill("solid", fgColor="F7F7F7")
    fill_fee_rate_zebra = PatternFill("solid", fgColor="F0F0F0")
    fill_result = PatternFill("solid", fgColor="FFF3E0")
    fill_final = PatternFill("solid", fgColor="FFEBEE")

    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center")
    right = Alignment(horizontal="right", vertical="center")

    # 范围摘要 + 核价口径（本批快照参数）
    meta_parts: list[str] = []
    density_text = "7.85"
    loss_rate_text = "0.003"
    loss_permille_text = "3"
    recovery_text = "0.97"
    recovery_percent_text = "97"
    if rows:
        sample = rows[0]
        if sample.year and sample.month:
            meta_parts.append(f"{sample.year}年{sample.month}月")
        if sample.location:
            meta_parts.append(str(sample.location))
        if sample.stamping_supplier:
            meta_parts.append(str(sample.stamping_supplier))
        density = to_decimal(getattr(sample, "density", None))
        loss_rate = to_decimal(getattr(sample, "material_loss_rate", None))
        recovery = to_decimal(getattr(sample, "scrap_recovery_rate", None))
        if density is not None:
            density_text = formula_number(density)
        if loss_rate is not None:
            loss_rate_text = formula_number(loss_rate)
            loss_permille_text = formula_number(loss_rate * PERMILLE)
        if recovery is not None:
            recovery_text = formula_number(recovery)
            recovery_percent_text = formula_number(recovery * PERCENT)
    meta_text = " · ".join(meta_parts) if meta_parts else "按筛选条件导出"
    formula_hint = (
        f"核价口径："
        f"P=M×N×J×ρ_steel÷1,000,000÷O；"
        f"R=P−K；"
        f"U=P×S×(1+λ)−P×λ×η×T−R×η×T；"
        f"直接成本=U+V+W+X；"
        f"最终价=直接成本+仓储包装费+管理费+财务费+税前利润。"
        f"拼焊件按子片分行：J/M/N/S 各片一格；"
        f"子片 P=M×N×J×ρ/1e6/O；"
        f"总成 R=SUM(P)−K，U=Σ(Pi×Si×(1+λ))−SUM(P)×λ×η×T−R×η×T。"
        f"其中 ρ_steel={density_text} g/cm³，"
        f"λ={loss_rate_text}（{loss_permille_text}‰），"
        f"η={recovery_text}（{recovery_percent_text}%），"
        f"S/T 为元/kg（吨价÷1000；S 含本月摆剪加价），"
        f"÷1,000,000 为 mm·g/cm³ → kg 量纲换算。"
    )

    # Row 1 标题
    sheet.merge_cells(f"A1:{last_col_letter}1")
    title_cell = sheet["A1"]
    title_cell.value = "冲压零件核价结果（材料费 + 加工费 + 模具费 + 检具费）"
    title_cell.font = title_font
    title_cell.fill = fill_title
    title_cell.alignment = Alignment(horizontal="left", vertical="center")
    for col in range(1, last_col + 1):
        sheet.cell(1, col).fill = fill_title
        sheet.cell(1, col).border = thin
    sheet.row_dimensions[1].height = 28

    # Row 2 说明
    sheet.merge_cells(f"A2:{last_col_letter}2")
    meta_cell = sheet["A2"]
    meta_cell.value = (
        f"{meta_text}　|　共 {len(rows)} 件　|　{formula_hint}"
        f"　|　AE~AJ 人可读溯源可核对/补填；AK~AO 为关联 ID"
        f"　|　B/C 冲压工厂与版本弱化显示"
    )
    meta_cell.font = meta_font
    meta_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    for col in range(1, last_col + 1):
        sheet.cell(2, col).fill = fill_title
        sheet.cell(2, col).border = thin
    sheet.row_dimensions[2].height = 48

    # Row 3 分组表头
    group_fills = {
        range(1, 4): fill_group_id,
        range(4, 13): fill_group_product,
        range(13, 22): fill_group_process,
        range(22, 23): fill_group_fee,
        range(23, 25): fill_group_fee,
        range(25, 26): fill_group_fee,
        range(26, 30): fill_group_fee_rate,
        range(30, 31): fill_group_final,
        range(31, 37): fill_group_trace,
        range(37, 42): fill_group_trace,
        range(42, 44): fill_group_product,
        range(44, 46): fill_group_id,
    }
    for merge_range, label in (
        ("A3:C3", "标识"),
        ("D3:L3", "产品信息"),
        ("M3:U3", "材料费"),
        ("V3:V3", "加工费"),
        ("W3:W3", "模具费"),
        ("X3:X3", "检具费"),
        ("Y3:Y3", "直接成本"),
        ("Z3:AC3", "成品费率费用"),
        ("AD3:AD3", "最终价"),
        ("AE3:AJ3", "溯源"),
        ("AK3:AO3", "关联ID"),
        ("AP3:AQ3", "利废"),
        ("AR3:AS3", "摆剪"),
    ):
        sheet.merge_cells(merge_range)
        cell = sheet[merge_range.split(":")[0]]
        cell.value = label
        cell.font = group_font
        cell.alignment = center
    for col in range(1, last_col + 1):
        cell = sheet.cell(3, col)
        cell.border = thin
        cell.font = group_font
        cell.alignment = center
        for col_range, fill in group_fills.items():
            if col in col_range:
                cell.fill = fill
                break
    sheet.row_dimensions[3].height = 22

    # Row 4 列名
    for col_letter, title in PROCESS_SHEET_HEADERS:
        cell = sheet[f"{col_letter}4"]
        cell.value = title
        is_trace = col_letter in trace_cols
        is_fee_rate = col_letter in fee_rate_cols
        is_scope_weak = col_letter in _SCOPE_WEAK_COLS
        if is_trace or is_fee_rate or is_scope_weak:
            cell.font = weak_header_font
        else:
            cell.font = header_font
        if is_trace or is_scope_weak:
            cell.fill = fill_header_trace
        elif is_fee_rate:
            cell.fill = fill_header_fee_rate
        else:
            cell.fill = fill_header
        cell.alignment = center
        cell.border = thin
    sheet.row_dimensions[4].height = 40

    last_data_row = write_process_data_rows(
        sheet,
        db,
        rows,
        bom_snapshot_repo=bom_snapshot_repo,
        bom_node_repo=bom_node_repo,
        steel_price_repo=steel_price_repo,
        scrap_price_repo=scrap_price_repo,
        process_fee_repo=process_fee_repo,
        warehouse_packaging_rate=warehouse_packaging_rate,
        management_rate=management_rate,
        finance_rate=finance_rate,
        pretax_profit_rate=pretax_profit_rate,
        thin=thin,
        data_font=data_font,
        weak_data_font=weak_data_font,
        fee_rate_font=fee_rate_font,
        accent_font=accent_font,
        fill_final=fill_final,
        fill_result=fill_result,
        fill_fee_rate=fill_fee_rate,
        fill_fee_rate_zebra=fill_fee_rate_zebra,
        fill_zebra_trace=fill_zebra_trace,
        fill_zebra=fill_zebra,
        center=center,
        left=left,
        right=right,
        trace_cols=trace_cols,
        id_cols=id_cols,
        fee_rate_cols=fee_rate_cols,
    )

    widths = {
        "A": 6,
        "B": 12,
        "C": 10,
        "D": 22,
        "E": 14,
        "F": 8,
        "G": 20,
        "H": 10,
        "I": 14,
        "J": 12,
        "K": 9,
        "L": 18,
        "M": 14,
        "N": 14,
        "O": 10,
        "P": 14,
        "Q": 11,
        "R": 10,
        "S": 16,
        "T": 13,
        "U": 12,
        "V": 10,
        "W": 10,
        "X": 10,
        "Y": 11,
        "Z": 10,
        "AA": 10,
        "AB": 12,
        "AC": 10,
        "AD": 11,
        "AE": 28,
        "AF": 14,
        "AG": 8,
        "AH": 42,
        "AI": 28,
        "AJ": 36,
        "AK": 10,
        "AL": 10,
        "AM": 10,
        "AN": 10,
        "AO": 10,
        "AP": 10,
        "AQ": 14,
        "AR": 10,
        "AS": 16,
    }
    for col_letter, width in widths.items():
        sheet.column_dimensions[col_letter].width = width

    sheet.freeze_panes = "G5"  # 冻结至短码列（A~F：序号/工厂/版本/总成供货号/零件号/短码）
    if rows:
        sheet.auto_filter.ref = f"A4:{last_col_letter}{last_data_row}"
    sheet.print_title_rows = "1:4"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0

    write_formula_note_sheet(
        workbook,
        density_text=density_text,
        loss_rate_text=loss_rate_text,
        loss_permille_text=loss_permille_text,
        recovery_text=recovery_text,
        recovery_percent_text=recovery_percent_text,
        thin=thin,
        center=center,
        left=left,
        meta_font=meta_font,
    )
    return sheet.title, len(rows)


def export_process_sheet(
    db: Session,
    rows: list[StampingPartCost],
    *,
    bom_snapshot_repo: BomSnapshotRepository,
    bom_node_repo: BomNodeRepository,
    steel_price_repo: SteelPriceRepository,
    scrap_price_repo: StampingScrapPriceRepository,
    process_fee_repo: StampingProcessFeeRepository,
    year: int | None = None,
    month: int | None = None,
    location: str | None = None,
    stamping_supplier: str | None = None,
    vehicle_model: str | None = None,
    version: str | None = None,
    current_user: UserVO,
) -> tuple[bytes, str]:
    """
    工艺清单口径：对齐样例至 S 列 + 加工费 + 模具费 + 检具费 + 成品费率费用 + 最终价。
    普通件一行一件，N/O/P/J/S 保留 Excel 公式；
    直接成本 W=S+T+U+V；四项费用（仓储包装→管理→财务→税前利润）=W×费率；最终价=W+四项。
    拼焊件按子片分行（料厚/长/宽/单价各片一格），净重与成本等列合并；
    子片 N 引用本行 H/K/L/M，总成 P/O/S 引用各子片行。
    总成供货号：同基地 BOM 上溯 L0；多总成时逗号分隔。
    零件号后为短码（数字体末四位）。
    末尾 AC~AH 为人可读溯源（核对/手工补填），AI~AM 为关联 ID。
    """
    workbook = Workbook()
    write_process_sheet_to_workbook(
        workbook,
        db,
        rows,
        bom_snapshot_repo=bom_snapshot_repo,
        bom_node_repo=bom_node_repo,
        steel_price_repo=steel_price_repo,
        scrap_price_repo=scrap_price_repo,
        process_fee_repo=process_fee_repo,
    )

    content = workbook_to_xlsx_bytes(workbook, current_user)
    filename = build_process_sheet_filename(
        rows,
        year=year,
        month=month,
        location=location,
        stamping_supplier=stamping_supplier,
        vehicle_model=vehicle_model,
        version=version,
    )
    logger.info("导出冲压零件核价结果 %s 条 → %s", len(rows), filename)
    return content, filename
