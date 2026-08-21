"""工艺清单口径 Excel 导出。"""

from __future__ import annotations

from typing import Any


import logging
from decimal import Decimal
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sqlalchemy.orm import Session

from app.common.excel_workbook import resolve_worksheet
from app.common.timezone import now
from app.repositories.bom.bom_repository import BomNodeRepository, BomSnapshotRepository
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)
from app.repositories.yishiyiyi.scrap_price.scrap_price_repository import (
    StampingScrapPriceRepository,
)
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.services.costing.stamping_part_cost.export.bom_resolver import (
    resolve_assembly_supply_no,
)
from app.services.costing.stamping_part_cost.export.formatters import formula_number
from app.services.costing.stamping_part_cost.export.tailor_weld_display import (
    blank_term_has_mass_inputs,
    build_blank_row_m_formula,
    build_steel_price_index,
    build_tailor_group_n_formula,
    build_tailor_group_o_formula,
    build_tailor_group_r_formula,
    load_blanks_by_part_id,
    resolve_part_cost_display,
)
from app.services.costing.stamping_part_cost.export.trace_lookups import load_trace_maps
from app.services.settings.system.settings_service import SettingsService
from app.services.costing.stamping_part_cost.helpers import (
    DEFAULT_MATERIAL_LOSS_RATE,
    DEFAULT_SCRAP_RECOVERY_RATE,
    DEFAULT_STEEL_DENSITY,
    format_number as _num,
    format_process_fee_trace,
    format_scrap_price_trace,
    format_steel_price_excel_trace,
    part_excel_row_col,
    to_decimal,
)

logger = logging.getLogger("service.stamping_part_cost_export")

_PROCESS_COL_LETTERS = (
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "AA",
    "AB",
    "AC",
    "AD",
    "AE",
    "AF",
    "AG",
    "AH",
)
# 拼焊总成共用列：跨子片行合并（料厚/长/宽/消耗/单价等按片分行）
_TAILOR_MERGED_COLS = frozenset(
    {
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "H",
        "N",
        "O",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
        "AA",
        "AB",
        "AD",
        "AE",
        "AG",
        "AH",
    }
)
_NUMBER_COLS = frozenset(
    {
        "G",
        "H",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
    }
)
_TRACE_COLS = frozenset(
    {"Z", "AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH"}
)
_ID_COLS = frozenset({"AF", "AG", "AH"})
_RESULT_COLS = frozenset({"R"})
_FINAL_COLS = frozenset({"Y"})
_FEE_RATE_COLS = frozenset({"U", "V", "W", "X"})
_TEXT_LEFT_COLS = frozenset({"B", "C", "D", "E", "F", "I"})
_FILENAME_ILLEGAL = '<>:"/\\|?*'


def _finished_fee_formula_cells(
    excel_row: int,
    *,
    warehouse_packaging_rate: Decimal,
    management_rate: Decimal,
    finance_rate: Decimal,
    pretax_profit_rate: Decimal,
) -> dict[str, object]:
    """直接成本 + 四项费用（固定顺序）+ 最终价，均为 Excel 公式。

    顺序：仓储+包装 → 管理费 → 财务费 → 税前利润
    费率须为系统配置 Decimal（禁止用费用÷直接成本反推，会出脏小数）。
    """
    t = f"T{excel_row}"
    return {
        "T": f"=R{excel_row}+S{excel_row}",
        "U": f"={t}*{formula_number(warehouse_packaging_rate)}",
        "V": f"={t}*{formula_number(management_rate)}",
        "W": f"={t}*{formula_number(finance_rate)}",
        "X": f"={t}*{formula_number(pretax_profit_rate)}",
        "Y": f"={t}+U{excel_row}+V{excel_row}+W{excel_row}+X{excel_row}",
    }


def _filename_token(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    for char in _FILENAME_ILLEGAL:
        text = text.replace(char, "")
    text = " ".join(text.split())
    return text or None


def _unique_row_value(rows: list[Any], attr: str) -> object | None:
    values = {getattr(row, attr, None) for row in rows}
    values.discard(None)
    values.discard("")
    if len(values) != 1:
        return None
    return next(iter(values))


def _unique_row_int(rows: list[Any], attr: str) -> int | None:
    raw = _unique_row_value(rows, attr)
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if text.isdigit():
            return int(text)
    return None


def build_process_sheet_filename(
    rows: list[Any],
    *,
    year: int | None = None,
    month: int | None = None,
    location: str | None = None,
    stamping_supplier: str | None = None,
    vehicle_model: str | None = None,
    version: str | None = None,
) -> str:
    """冲压零件核价结果导出文件名：年月 + 基地 + 工厂 + 车型版本（有则带上）。"""
    year_value = year if year is not None else _unique_row_int(rows, "year")
    month_value = month if month is not None else _unique_row_int(rows, "month")
    location_value = location or _unique_row_value(rows, "location")
    supplier_value = stamping_supplier or _unique_row_value(
        rows, "stamping_supplier"
    )
    vehicle_value = vehicle_model or _unique_row_value(rows, "vehicle_model")
    version_value = version or _unique_row_value(rows, "version")

    parts = ["冲压零件核价结果"]
    if year_value is not None and month_value is not None:
        parts.append(f"{year_value}年{month_value}月")
    elif year_value is not None:
        parts.append(f"{year_value}年")
    for token in (
        _filename_token(location_value),
        _filename_token(supplier_value),
        _filename_token(vehicle_value),
        _filename_token(version_value),
    ):
        if token:
            parts.append(token)
    stamp = now().strftime("%Y%m%d_%H%M%S")
    return "_".join(parts) + f"_{stamp}.xlsx"


def _part_size_formula(material_row: int, thickness_row: int) -> str:
    """零件尺寸 = 材质-料厚；整数料厚用 TEXT 保留 1 位小数。"""
    return f'=F{material_row}&"-"&TEXT(G{thickness_row},"0.0###")'


def write_process_sheet_to_workbook(
    workbook: Workbook,
    db: Session,
    rows: list[Any],
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
    sheet_title: str = "冲压核价结果",
) -> tuple[str, int]:
    """
    将工艺清单口径核价结果写入已有 Workbook（不 save）。
    返回 (主表 sheet 名, 主表零件行数近似用 rows 长度)。
    """
    sheet = resolve_worksheet(workbook, sheet_title)

    last_col = 34  # AH
    last_col_letter = "AH"
    trace_cols = _TRACE_COLS
    id_cols = _ID_COLS
    fee_rate_cols = _FEE_RATE_COLS

    settings_service = SettingsService()
    warehouse_packaging_rate = (
        settings_service.get_finished_warehouse_packaging_rate(db)
    )
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
            loss_permille_text = formula_number(loss_rate * Decimal("1000"))
        if recovery is not None:
            recovery_text = formula_number(recovery)
            recovery_percent_text = formula_number(recovery * Decimal("100"))
    meta_text = " · ".join(meta_parts) if meta_parts else "按筛选条件导出"
    formula_hint = (
        f"核价口径："
        f"M=L×W×T×ρ_steel÷1,000,000÷n；"
        f"O=M−H；"
        f"R=M×P×(1+λ)−M×λ×η×Q−O×η×Q；"
        f"直接成本=R+S；"
        f"最终价=直接成本+仓储包装费+管理费+财务费+税前利润。"
        f"拼焊件按子片分行：G/J/K/P 各片一格；"
        f"子片 M=J×K×G×ρ/1e6/L；"
        f"总成 O=SUM(M)−H，R=Σ(Mi×Pi×(1+λ))−SUM(M)×λ×η×Q−O×η×Q。"
        f"其中 ρ_steel={density_text} g/cm³，"
        f"λ={loss_rate_text}（{loss_permille_text}‰），"
        f"η={recovery_text}（{recovery_percent_text}%），"
        f"P/Q 为元/kg（吨价÷1000），"
        f"÷1,000,000 为 mm·g/cm³ → kg 量纲换算。"
    )

    # Row 1 标题
    sheet.merge_cells(f"A1:{last_col_letter}1")
    title_cell = sheet["A1"]
    title_cell.value = "冲压零件核价结果（材料费 + 加工费）"
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
        f"　|　Z~AE 人可读溯源可核对/补填；AF~AH 为关联 ID"
    )
    meta_cell.font = meta_font
    meta_cell.alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    for col in range(1, last_col + 1):
        sheet.cell(2, col).fill = fill_title
        sheet.cell(2, col).border = thin
    sheet.row_dimensions[2].height = 48

    # Row 3 分组表头
    group_fills = {
        range(1, 3): fill_group_id,
        range(3, 10): fill_group_product,
        range(10, 19): fill_group_process,
        range(19, 20): fill_group_fee,
        range(20, 21): fill_group_fee,
        range(21, 25): fill_group_fee_rate,
        range(25, 26): fill_group_final,
        range(26, 32): fill_group_trace,
        range(32, 35): fill_group_trace,
    }
    for merge_range, label in (
        ("A3:B3", "标识"),
        ("C3:I3", "产品信息"),
        ("J3:R3", "材料费"),
        ("S3:S3", "加工费"),
        ("T3:T3", "直接成本"),
        ("U3:X3", "成品费率费用"),
        ("Y3:Y3", "最终价"),
        ("Z3:AE3", "溯源"),
        ("AF3:AH3", "关联ID"),
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
    headers = [
        ("A", "序号"),
        ("B", "总成供货号"),
        ("C", "零件号"),
        ("D", "零件名称"),
        ("E", "零件简图"),
        ("F", "材质"),
        ("G", "料厚"),
        ("H", "净重"),
        ("I", "零件尺寸"),
        ("J", "长"),
        ("K", "宽(步距)"),
        ("L", "可制件数"),
        ("M", "预估单件材料消耗(KG)"),
        ("N", "材料利用率"),
        ("O", "废料重量"),
        ("P", "钢板单价(元/KG)"),
        ("Q", "废料单价(元/KG)"),
        ("R", "原材料成本"),
        ("S", "加工费"),
        ("T", "直接成本"),
        ("U", "仓储+包装"),
        ("V", "管理费"),
        ("W", "财务费"),
        ("X", "税前利润"),
        ("Y", "最终价"),
        ("Z", "来源Excel"),
        ("AA", "工作表"),
        ("AB", "行/列"),
        ("AC", "钢材价溯源"),
        ("AD", "废料价溯源"),
        ("AE", "加工费溯源"),
        ("AF", "钢材价ID"),
        ("AG", "废料价ID"),
        ("AH", "加工费ID"),
    ]
    for col_letter, title in headers:
        cell = sheet[f"{col_letter}4"]
        cell.value = title
        is_trace = col_letter in trace_cols
        is_fee_rate = col_letter in fee_rate_cols
        if is_trace or is_fee_rate:
            cell.font = weak_header_font
        else:
            cell.font = header_font
        if is_trace:
            cell.fill = fill_header_trace
        elif is_fee_rate:
            cell.fill = fill_header_fee_rate
        else:
            cell.fill = fill_header
        cell.alignment = center
        cell.border = thin
    sheet.row_dimensions[4].height = 40

    # 数据行
    data_start = 5
    number_cols = _NUMBER_COLS
    result_cols = _RESULT_COLS
    final_cols = _FINAL_COLS
    text_left_cols = _TEXT_LEFT_COLS
    snapshot_l0_cache: dict[tuple[str, str, str], dict[str, str]] = {}
    fill_plain = PatternFill("solid", fgColor="FFFFFF")

    steel_by_id, scrap_by_id, fee_by_id = load_trace_maps(
        db,
        rows,
        steel_price_repo=steel_price_repo,
        scrap_price_repo=scrap_price_repo,
        process_fee_repo=process_fee_repo,
    )
    blanks_by_part = load_blanks_by_part_id(db, rows)
    steel_index = build_steel_price_index(db, rows, steel_repo=steel_price_repo)

    def paint_data_row(excel_row: int, values: dict[str, object], zebra: bool) -> None:
        for col_letter in _PROCESS_COL_LETTERS:
            cell = sheet[f"{col_letter}{excel_row}"]
            if col_letter in values:
                cell.value = values[col_letter]
            is_trace = col_letter in trace_cols
            is_fee_rate = col_letter in fee_rate_cols
            if is_trace:
                cell.font = weak_data_font
            elif is_fee_rate:
                cell.font = fee_rate_font
            elif col_letter in final_cols:
                cell.font = accent_font
            else:
                cell.font = data_font
            cell.border = thin
            if col_letter in final_cols:
                cell.fill = fill_final
            elif col_letter in result_cols:
                cell.fill = fill_result
            elif is_fee_rate:
                cell.fill = fill_fee_rate_zebra if zebra else fill_fee_rate
            elif is_trace:
                cell.fill = fill_zebra_trace if zebra else fill_plain
            elif zebra:
                cell.fill = fill_zebra
            else:
                cell.fill = fill_plain

            if col_letter in {"AC", "AD", "AE"}:
                cell.alignment = Alignment(
                    horizontal="left", vertical="center", wrap_text=True
                )
            elif col_letter in id_cols:
                cell.alignment = center
            elif col_letter in text_left_cols or col_letter in {"Z", "AA"}:
                cell.alignment = left
            elif col_letter in number_cols or col_letter == "A":
                cell.alignment = right if col_letter != "A" else center
            else:
                cell.alignment = center

            if col_letter == "G":
                cell.number_format = "0.0###"
            elif col_letter in {"H", "P", "Q", "S"}:
                cell.number_format = "0.####"
            elif col_letter in {"J", "K"}:
                cell.number_format = "0.##"
            elif col_letter == "N":
                cell.number_format = "0.00%"
            elif col_letter in {"M", "O", "R", "T", "U", "V", "W", "X", "Y"}:
                cell.number_format = "0.0000"
            elif col_letter == "L":
                cell.number_format = "0"
            elif col_letter in id_cols:
                cell.number_format = "0"

        multi_line = any(
            isinstance(values.get(col), str) and "\n" in str(values.get(col))
            for col in ("AC", "AD", "AE")
        )
        sheet.row_dimensions[excel_row].height = 52 if multi_line else 18

    def merge_tailor_group(first_row: int, last_row: int) -> None:
        if last_row <= first_row:
            return
        for col_letter in _TAILOR_MERGED_COLS:
            sheet.merge_cells(f"{col_letter}{first_row}:{col_letter}{last_row}")

    excel_row = data_start
    for offset, row in enumerate(rows):
        density = to_decimal(getattr(row, "density", None)) or DEFAULT_STEEL_DENSITY
        loss_rate = (
            to_decimal(getattr(row, "material_loss_rate", None))
            or DEFAULT_MATERIAL_LOSS_RATE
        )
        recovery = (
            to_decimal(getattr(row, "scrap_recovery_rate", None))
            or DEFAULT_SCRAP_RECOVERY_RATE
        )
        display = resolve_part_cost_display(
            row,
            blanks_by_part.get(int(row.source_part_id or 0), []),
            steel_index,
        )
        scrap_ton = to_decimal(row.scrap_ton_price)
        scrap_kg = (scrap_ton / Decimal("1000")) if scrap_ton is not None else None
        assembly_supply_no = resolve_assembly_supply_no(
            db,
            bom_snapshot_repo=bom_snapshot_repo,
            bom_node_repo=bom_node_repo,
            location=row.location,
            vehicle_model=row.vehicle_model,
            version=row.version,
            part_number=row.part_number,
            snapshot_l0_cache=snapshot_l0_cache,
        )
        seq = row.seq_no if row.seq_no is not None else offset + 1
        zebra = offset % 2 == 1
        scrap_trace = format_scrap_price_trace(
            scrap_by_id.get(row.scrap_price_id)
            if row.scrap_price_id is not None
            else None
        )
        fee_trace = format_process_fee_trace(
            fee_by_id.get(row.process_fee_id)
            if row.process_fee_id is not None
            else None
        )
        process_fee_cell = (
            _num(row.process_fee_amount, 3)
            if row.process_fee_amount is not None
            else ""
        )

        if display.is_tailor_welded and len(display.blank_terms) >= 2:
            terms = display.blank_terms
            first_row = excel_row
            last_row = excel_row + len(terms) - 1
            priced_rows = [
                first_row + index
                for index, term in enumerate(terms)
                if blank_term_has_mass_inputs(term) and term.steel_kg_price is not None
            ]
            can_formula = len(priced_rows) == len(terms)
            group_n = build_tailor_group_n_formula(first_row, last_row)
            group_o = build_tailor_group_o_formula(first_row, last_row)
            if can_formula:
                group_r: Decimal | str = build_tailor_group_r_formula(
                    priced_rows,
                    first_row=first_row,
                    last_row=last_row,
                    loss_rate=loss_rate,
                    recovery=recovery,
                )
            else:
                material_r = to_decimal(row.material_net_per_part)
                group_r = material_r if material_r is not None else ""

            for index, term in enumerate(terms):
                blank_row = first_row + index
                blank_values: dict[str, object] = {
                    "G": (
                        _num(term.thickness, 4) if term.thickness is not None else ""
                    ),
                    "I": _part_size_formula(first_row, blank_row),
                    "J": (
                        _num(term.length, 2) if term.length is not None else ""
                    ),
                    "K": (
                        _num(term.width, 2) if term.width is not None else ""
                    ),
                    "L": (
                        term.parts_per_sheet
                        if term.parts_per_sheet is not None
                        else ""
                    ),
                    "M": (
                        build_blank_row_m_formula(blank_row, density)
                        if blank_term_has_mass_inputs(term)
                        else ""
                    ),
                    "P": (
                        float(term.steel_kg_price)
                        if term.steel_kg_price is not None
                        else ""
                    ),
                    "AC": format_steel_price_excel_trace(term.steel),
                    "AF": term.steel.id if term.steel is not None else "",
                }
                if index == 0:
                    blank_values.update(
                        {
                            "A": seq,
                            "B": assembly_supply_no,
                            "C": row.part_number or "",
                            "D": row.part_name or "",
                            "E": "",
                            "F": row.material or "",
                            "H": (
                                _num(row.part_weight, 4)
                                if row.part_weight is not None
                                else ""
                            ),
                            "N": group_n,
                            "O": group_o,
                            "Q": float(scrap_kg) if scrap_kg is not None else "",
                            "R": group_r,
                            "S": process_fee_cell,
                            **_finished_fee_formula_cells(
                                first_row,
                                warehouse_packaging_rate=warehouse_packaging_rate,
                                management_rate=management_rate,
                                finance_rate=finance_rate,
                                pretax_profit_rate=pretax_profit_rate,
                            ),
                            "Z": row.excel_filename or "",
                            "AA": row.excel_sheet_name or "",
                            "AB": part_excel_row_col(row),
                            "AD": scrap_trace,
                            "AE": fee_trace,
                            "AG": (
                                row.scrap_price_id
                                if row.scrap_price_id is not None
                                else ""
                            ),
                            "AH": (
                                row.process_fee_id
                                if row.process_fee_id is not None
                                else ""
                            ),
                        }
                    )
                paint_data_row(blank_row, blank_values, zebra)
            merge_tailor_group(first_row, last_row)
            excel_row = last_row + 1
            continue

        steel_ton = to_decimal(row.steel_ton_price)
        steel_kg = (steel_ton / Decimal("1000")) if steel_ton is not None else None
        values: dict[str, object] = {
            "A": seq,
            "B": assembly_supply_no,
            "C": row.part_number or "",
            "D": row.part_name or "",
            "E": "",
            "F": row.material or "",
            "G": _num(row.thickness, 4) if row.thickness is not None else "",
            "H": _num(row.part_weight, 4) if row.part_weight is not None else "",
            "I": _part_size_formula(excel_row, excel_row),
            "J": _num(row.sheet_length, 2) if row.sheet_length is not None else "",
            "K": _num(row.sheet_width, 2) if row.sheet_width is not None else "",
            "L": row.parts_per_sheet if row.parts_per_sheet is not None else "",
            "M": (
                f"=J{excel_row}*K{excel_row}*G{excel_row}"
                f"*{formula_number(density)}/1000000/L{excel_row}"
            ),
            "N": f"=H{excel_row}/M{excel_row}",
            "O": f"=M{excel_row}-H{excel_row}",
            "P": float(steel_kg) if steel_kg is not None else "",
            "Q": float(scrap_kg) if scrap_kg is not None else "",
            "R": (
                f"=M{excel_row}*P{excel_row}*(1+{formula_number(loss_rate)})"
                f"-M{excel_row}*{formula_number(loss_rate)}"
                f"*{formula_number(recovery)}*Q{excel_row}"
                f"-O{excel_row}*Q{excel_row}*{formula_number(recovery)}"
            ),
            "S": process_fee_cell,
            **_finished_fee_formula_cells(
                excel_row,
                warehouse_packaging_rate=warehouse_packaging_rate,
                management_rate=management_rate,
                finance_rate=finance_rate,
                pretax_profit_rate=pretax_profit_rate,
            ),
            "Z": row.excel_filename or "",
            "AA": row.excel_sheet_name or "",
            "AB": part_excel_row_col(row),
            "AC": format_steel_price_excel_trace(
                steel_by_id.get(row.steel_price_id)
                if row.steel_price_id is not None
                else None
            ),
            "AD": scrap_trace,
            "AE": fee_trace,
            "AF": row.steel_price_id if row.steel_price_id is not None else "",
            "AG": row.scrap_price_id if row.scrap_price_id is not None else "",
            "AH": row.process_fee_id if row.process_fee_id is not None else "",
        }
        paint_data_row(excel_row, values, zebra)
        excel_row += 1

    last_data_row = excel_row - 1 if rows else 4

    widths = {
        "A": 6,
        "B": 22,
        "C": 14,
        "D": 20,
        "E": 10,
        "F": 14,
        "G": 12,
        "H": 9,
        "I": 18,
        "J": 14,
        "K": 14,
        "L": 10,
        "M": 14,
        "N": 11,
        "O": 10,
        "P": 16,
        "Q": 13,
        "R": 12,
        "S": 10,
        "T": 11,
        "U": 10,
        "V": 10,
        "W": 12,
        "X": 10,
        "Y": 11,
        "Z": 28,
        "AA": 14,
        "AB": 8,
        "AC": 42,
        "AD": 28,
        "AE": 36,
        "AF": 10,
        "AG": 10,
        "AH": 10,
    }
    for col_letter, width in widths.items():
        sheet.column_dimensions[col_letter].width = width

    sheet.freeze_panes = "D5"  # 冻结至零件号列（A~C：序号/总成供货号/零件号）
    if rows:
        sheet.auto_filter.ref = f"A4:{last_col_letter}{last_data_row}"
    sheet.print_title_rows = "1:4"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToPage = True
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0

    # 附录：核价口径定义（次于「单件」工作表，打开文件默认见单件）
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
        ("L, W, T", "板料长、宽(步距)、料厚", "mm；拼焊件每个子片单独一行"),
        ("n", "可制件数", "件/板；拼焊件按子片行填写"),
        ("ρ_steel", "钢材密度", f"{density_text} g/cm³"),
        ("1,000,000", "量纲换算系数", "mm³·(g/cm³) → kg"),
        (
            "M",
            "预估单件材料消耗",
            "普通件 / 拼焊子片行：=J×K×G×ρ/1e6/L；"
            "总成消耗 = SUM(各子片 M)",
        ),
        ("H", "零件净重", "kg；拼焊件为焊后总成净重，跨子片行合并"),
        ("O", "废料重量", "普通件 O=M−H；拼焊件 O=SUM(M)−H（合并格）"),
        (
            "P",
            "钢板单价",
            "元/kg（吨价÷1000）；拼焊件各子片一行各自单价",
        ),
        ("Q", "废料单价", "元/kg（吨价÷1000）"),
        ("λ", "材料损耗率", f"{loss_rate_text}（{loss_permille_text}‰）"),
        ("η", "废料回收率", f"{recovery_text}（{recovery_percent_text}%）"),
        ("①", "钢材采购额", "普通件 M×P×(1+λ)；拼焊件 Σ(Mi×Pi×(1+λ))"),
        ("②", "损耗废料扣除", "M×λ×η×Q（拼焊件与 Σ Mi×λ×η×Q 等价）"),
        ("③", "边角废料扣除", "O × η × Q（总成一次）"),
        (
            "R",
            "原材料成本",
            "普通件：=M×P×(1+λ)−M×λ×η×Q−O×η×Q；"
            "拼焊件：=Σ(Mi×Pi×(1+λ))−SUM(M)×λ×η×Q−O×η×Q（引用各子片行）",
        ),
        ("S", "加工费", "元/件；取自加工费核算结果（拼焊父件一行）"),
        ("T", "直接成本", "R + S"),
        ("U", "仓储+包装", "直接成本 × 仓储+包装管理费用率"),
        ("V", "管理费", "直接成本 × 管理费率"),
        ("W", "财务费", "直接成本 × 财务费率"),
        ("X", "税前利润", "直接成本 × 税前利润率"),
        (
            "Y",
            "最终价",
            "直接成本 + 仓储包装费 + 管理费 + 财务费 + 税前利润"
            "（计算时按系统设置费率落库；导出列为公式）",
        ),
        (
            "Z~AE",
            "溯源（弱化）",
            "按文件/表/行定位核对；钢材含基价·厚度·宽度·锌层；"
            "拼焊件可含多条钢材价；废料为基地年月净价；"
            "加工费为工艺文件+工序依据。单元格可手工补填。",
        ),
        (
            "AF~AH",
            "关联ID（弱化）",
            "钢材价ID / 废料价ID / 加工费ID；拼焊件钢材价ID 按子片分行。",
        ),
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

    # 附录：负公差说明（通俗口径，供采购/核价对照）
    tip = resolve_worksheet(workbook, "冲压负公差说明")
    tip_title_font = Font(name="微软雅黑", size=12, bold=True, color="1F1F1F")
    tip_section_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
    tip_body_font = Font(name="微软雅黑", size=10, color="333333")
    tip_section_fill = PatternFill("solid", fgColor="455A64")
    tip_warn_fill = PatternFill("solid", fgColor="FFF3E0")
    tip_wrap = Alignment(horizontal="left", vertical="center", wrap_text=True)

    tip["A1"] = "为什么「负公差供料」时，按本表核价采购冲压件可能吃亏？"
    tip["A1"].font = tip_title_font
    tip.merge_cells("A1:B1")
    tip.row_dimensions[1].height = 28

    tip["A2"] = (
        "本页是业务提醒，不是改公式。核价仍按「单件」「核价口径」页执行；"
        "这里只说明：名义料厚核价 与 负公差实料 之间，钱差在哪里。"
    )
    tip["A2"].font = meta_font
    tip.merge_cells("A2:B2")
    tip.row_dimensions[2].height = 36

    tip_sections: list[tuple[str, str]] = [
        (
            "一句话结论",
            "本表用工艺卡上的「名义料厚」算材料消耗；钢厂/冲压厂实际常按「负公差」"
            "（比名义更薄一点）交货。按名义厚度核出来的采购价，往往高于供应商真实用料成本——"
            "差额多半落在供应商侧，采购侧更容易吃亏。",
        ),
        (
            "本表怎么算材料",
            "预估单件材料消耗 M ≈ 长 × 宽 × 料厚 × 密度 ÷ 可制件数。"
            "料厚取工艺文件里的名义值（例如写 0.80mm），"
            "公式里没有再扣「厚度公差」。钢材价也按名义厚度档匹配。",
        ),
        (
            "负公差是什么意思",
            "钢板允许在标准范围内略薄于名义厚度交货，例如名义 0.80mm，"
            "实际可能到 0.76mm 左右。这叫负公差，通常仍合格，行业里很常见。"
            "同面积的料片，实际更薄 → 实际更轻 → 按吨买钢时，开出同样多片料更省吨。",
        ),
        (
            "钱差怎么来的（通俗对比）",
            "① 核价侧：按名义厚度算 M → 材料费偏「厚」→ 冲压件最终价偏高；"
            "② 供应商用料：常拿到负公差板 → 同样开料更省钢材重量 → 真实材料成本偏低；"
            "③ 结果：采购侧按「偏厚」的理论价买件，供应商按「偏薄」的实料做件，"
            "厚度差变成供应商利润空间。"
            "粗算：厚度薄 5%，材料费部分大约也高估约 5%（加工费等另计）。",
        ),
        (
            "为什么净重/废料扣不回来",
            "表里的零件净重多半也是工艺/理论重，不是入厂实称。"
            "名义厚度算消耗、名义净重算废料，纸面上自洽，"
            "但负公差带来的「实料更轻」不会自动反映到核价里把采购价扣回去。"
            "钢材联动价通常仍落在同一厚度价档，也不会因为更薄就自动降吨价补偿。",
        ),
        (
            "这不是公式写错",
            "名义厚度核价是常见采购侧口径，便于统一、可复核。"
            "吃亏来自「名义核价 vs 负公差供料」的行业价差，不是 Excel 公式算错。"
            "要收口，靠商务/工艺约定，而不是改长×宽×厚本身。",
        ),
        (
            "实务上可以怎么谈",
            "① 合同约定交货厚度带（中值、禁止极端负公差等）；"
            "② 大宗件抽检实厚，超约定则议价或补差；"
            "③ 个别高额件单独谈厚度补偿或按中值核价；"
            "④ 与冲压厂、钢厂口径对齐后再锁年度价。"
            "具体条款以采购与质量约定为准，本页仅作核价对照说明。",
        ),
    ]
    row_idx = 4
    for section_title, section_body in tip_sections:
        title_cell = tip.cell(row_idx, 1, section_title)
        title_cell.font = tip_section_font
        title_cell.fill = tip_section_fill
        title_cell.alignment = tip_wrap
        title_cell.border = thin
        tip.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=2)
        tip.row_dimensions[row_idx].height = 22
        row_idx += 1

        body_cell = tip.cell(row_idx, 1, section_body)
        body_cell.font = tip_body_font
        body_cell.alignment = tip_wrap
        body_cell.border = thin
        if section_title == "一句话结论":
            body_cell.fill = tip_warn_fill
        tip.merge_cells(start_row=row_idx, start_column=1, end_row=row_idx, end_column=2)
        tip.cell(row_idx, 2).border = thin
        tip.row_dimensions[row_idx].height = 72 if len(section_body) > 80 else 48
        row_idx += 2

    tip.column_dimensions["A"].width = 22
    tip.column_dimensions["B"].width = 88

    return sheet.title, len(rows)


def export_process_sheet(
    db: Session,
    rows: list[Any],
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
) -> tuple[bytes, str]:
    """
    工艺清单口径：对齐样例至 R 列 + 加工费 + 成品费率费用 + 最终价。
    普通件一行一件，M/N/O/I/R 保留 Excel 公式；
    直接成本 T=R+S；四项费用（仓储包装→管理→财务→税前利润）=T×费率；最终价=T+四项。
    拼焊件按子片分行（料厚/长/宽/单价各片一格），净重与成本等列合并；
    子片 M 引用本行 G/J/K/L，总成 O/N/R 引用各子片行。
    总成供货号：同基地 BOM 上溯 L0；多总成时逗号分隔。
    末尾 Z~AE 为人可读溯源（核对/手工补填），AF~AH 为关联 ID（钢材/废料/加工费）。
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
        year=year,
        month=month,
        location=location,
        stamping_supplier=stamping_supplier,
        vehicle_model=vehicle_model,
        version=version,
    )

    buffer = BytesIO()
    workbook.save(buffer)
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
    return buffer.getvalue(), filename
