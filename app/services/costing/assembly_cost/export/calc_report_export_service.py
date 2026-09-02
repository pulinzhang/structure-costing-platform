"""总成核价计算报告 Excel（封面摘要 + 核价卡 + 过程说明）。"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from decimal import Decimal
from typing import Literal

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy.orm import Session

from app.common.excel_workbook import resolve_worksheet
from app.common.export_watermark import workbook_to_xlsx_bytes
from app.common.money import Q4, excel_money_cell
from app.common.timezone import now
from app.schemas.vo.assembly_cost_vo import (
    AssemblyCostCalcCardTraceVO,
    AssemblyCostCalcLogVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.assembly_cost.calc.calc_log_service import (
    AssemblyCostCalcLogService,
)

logger = logging.getLogger("service.assembly_cost.calc_report_export")

_FONT = "微软雅黑"
_MONEY_FORMAT = "0.0000"
_ACCENT = "9F1239"
_INK = "1C1917"
_MUTED = "57534E"
_PAPER = "FFFDF8"
_CREAM = "FAF7F2"

_STATUS_LABEL: dict[str, str] = {
    "ok": "成功",
    "partial": "部分成功",
    "failed": "失败",
    "skipped": "跳过",
    "processing": "计算中",
    "success": "成功",
}

_STATUS_COLOR: dict[str, str] = {
    "ok": "166534",
    "partial": "B45309",
    "failed": "B91C1C",
    "skipped": "57534E",
    "processing": "1D4ED8",
    "success": "166534",
}

_CARD_HEADERS = [
    "序号",
    "层级",
    "树根",
    "零件号",
    "零件名称",
    "对象类型",
    "状态",
    "材料",
    "焊接",
    "应成本",
    "总费用",
    "缺价件数",
    "说明",
    "缺价零件",
]
_CARD_WIDTHS = [6, 8, 8, 18, 22, 14, 12, 12, 12, 12, 12, 10, 36, 28]
_MONEY_COLS = {8, 9, 10, 11}
_KPI_COL = 11

TreeRootFilter = Literal["all", "yes", "no"]


def _fill(hex_color: str) -> PatternFill:
    return PatternFill(start_color=hex_color, end_color=hex_color, fill_type="solid")


def _font(*, size: int = 10, bold: bool = False, color: str = "000000") -> Font:
    return Font(name=_FONT, size=size, bold=bold, color=color)


def _thin() -> Border:
    side = Side(style="thin", color="E7E5E4")
    return Border(left=side, right=side, top=side, bottom=side)


def _num(value: object) -> Decimal | str:
    return excel_money_cell(value, Q4, allow_negative=True)


def _when(value: datetime | None) -> str:
    if value is None:
        return "—"
    return f"{value:%Y-%m-%d %H:%M:%S}"


def _safe_token(value: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", value).strip(" ._")
    return cleaned or "报告"


def match_calc_report_card(
    card: AssemblyCostCalcCardTraceVO,
    *,
    keyword: str | None = None,
    status: str | None = None,
    level: int | None = None,
    tree_root: TreeRootFilter = "all",
) -> bool:
    if status and card.status != status:
        return False
    if level is not None and card.level != level:
        return False
    if tree_root == "yes" and not card.is_tree_root:
        return False
    if tree_root == "no" and card.is_tree_root:
        return False
    needle = (keyword or "").strip().lower()
    if not needle:
        return True
    hay = " ".join(
        [
            card.part_number or "",
            card.part_name or "",
            card.message or "",
            card.object_kind or "",
            *card.missing_parts,
        ]
    ).lower()
    return needle in hay


class AssemblyCostCalcReportExportService:
    """把计算日志导出为与浅色报告页同口径的 Excel。"""

    def __init__(self, calc_log_service: AssemblyCostCalcLogService | None = None) -> None:
        self.calc_log_service = calc_log_service or AssemblyCostCalcLogService()
        self._center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        self._left = Alignment(horizontal="left", vertical="center", wrap_text=True)
        self._right = Alignment(horizontal="right", vertical="center")
        self._indent = Alignment(horizontal="left", vertical="center", wrap_text=True, indent=1)

    def export(
        self,
        db: Session,
        *,
        log_id: int,
        keyword: str | None = None,
        status: str | None = None,
        level: int | None = None,
        tree_root: TreeRootFilter = "all",
        current_user: UserVO,
    ) -> tuple[bytes, str]:
        log = self.calc_log_service.get_calc_log(db, log_id)
        cards = [
            card
            for card in log.cards
            if match_calc_report_card(
                card,
                keyword=keyword,
                status=status,
                level=level,
                tree_root=tree_root,
            )
        ]
        wb = Workbook()
        self.write_to_workbook(
            wb,
            log,
            cards,
            keyword=keyword,
            status=status,
            level=level,
            tree_root=tree_root,
        )
        period = f"{log.year}-{log.month:02d}"
        stamp = now().strftime("%Y%m%d_%H%M%S")
        filename = (
            f"总成核价计算报告_{_safe_token(log.location)}"
            f"_{_safe_token(log.vehicle_model)}_{period}_{stamp}.xlsx"
        )
        content = workbook_to_xlsx_bytes(wb, current_user)
        logger.info(
            "导出计算报告 Excel: log_id=%s filename=%s cards=%d/%d",
            log_id,
            filename,
            len(cards),
            len(log.cards),
        )
        return content, filename

    def write_to_workbook(
        self,
        wb: Workbook,
        log: AssemblyCostCalcLogVO,
        cards: list[AssemblyCostCalcCardTraceVO],
        *,
        keyword: str | None = None,
        status: str | None = None,
        level: int | None = None,
        tree_root: TreeRootFilter = "all",
    ) -> None:
        filter_text = self._filter_text(
            keyword=keyword,
            status=status,
            level=level,
            tree_root=tree_root,
            shown=len(cards),
            total=len(log.cards),
        )
        self._write_cover(resolve_worksheet(wb, "封面摘要"), log, filter_text)
        self._write_cards(resolve_worksheet(wb, "核价卡"), log, cards, filter_text)
        self._write_narrative(resolve_worksheet(wb, "过程说明"), log)

    @staticmethod
    def _filter_text(
        *,
        keyword: str | None,
        status: str | None,
        level: int | None,
        tree_root: TreeRootFilter,
        shown: int,
        total: int,
    ) -> str:
        parts: list[str] = [f"显示 {shown} / {total} 张卡"]
        if status:
            parts.append(_STATUS_LABEL.get(status, status))
        if level is not None:
            parts.append(f"L{level}")
        if tree_root == "yes":
            parts.append("仅树根")
        elif tree_root == "no":
            parts.append("非树根")
        if keyword and keyword.strip():
            parts.append(f"关键词 {keyword.strip()}")
        return " · ".join(parts)

    def _write_cover(
        self,
        ws: Worksheet,
        log: AssemblyCostCalcLogVO,
        filter_text: str,
    ) -> None:
        ws.sheet_properties.tabColor = _ACCENT
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 1
        ws.sheet_view.showGridLines = False
        ws.column_dimensions["A"].width = 16
        ws.column_dimensions["B"].width = 28
        ws.column_dimensions["C"].width = 16
        ws.column_dimensions["D"].width = 28

        ws.merge_cells("A1:D1")
        title = ws["A1"]
        title.value = "总成核价计算报告"
        title.font = _font(size=20, bold=True, color="FFFFFF")
        title.fill = _fill(_ACCENT)
        title.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        ws.row_dimensions[1].height = 36

        ws.merge_cells("A2:D2")
        sub = ws["A2"]
        sub.value = (
            f"Assembly Costing Process Report  ·  {filter_text}"
            f"  ·  导出 {now().strftime('%Y-%m-%d %H:%M')}"
        )
        sub.font = _font(size=9, color=_MUTED)
        sub.fill = _fill(_CREAM)
        sub.alignment = self._indent
        ws.row_dimensions[2].height = 22

        period = f"{log.year}-{log.month:02d}"
        rows: list[tuple[str, str, str, str]] = [
            ("范围", f"{log.location} / {log.vehicle_model} / {log.bom_version}", "核价期", period),
            (
                "状态",
                _STATUS_LABEL.get(log.status, log.status),
                "操作人",
                log.operator_name or "—",
            ),
            ("开始", _when(log.started_at), "结束", _when(log.finished_at)),
            (
                "核价卡",
                str(log.subject_total if log.subject_total is not None else log.l0_total or 0),
                "批次",
                log.calc_batch_id,
            ),
            (
                "成功",
                str(log.ok_count),
                "部分成功",
                str(log.partial_count),
            ),
            (
                "失败",
                str(log.failed_count),
                "跳过",
                str(log.skipped_approved_count),
            ),
        ]
        start = 4
        for offset, (label_a, value_a, label_b, value_b) in enumerate(rows):
            row = start + offset
            for col, (label, value) in enumerate(
                ((label_a, value_a), (label_b, value_b)),
                start=1,
            ):
                label_cell = ws.cell(row=row, column=col * 2 - 1, value=label)
                label_cell.font = _font(size=9, color=_MUTED)
                label_cell.fill = _fill(_CREAM)
                label_cell.alignment = self._indent
                value_cell = ws.cell(row=row, column=col * 2, value=value)
                value_cell.font = _font(size=11, bold=True, color=_INK)
                value_cell.fill = _fill(_PAPER)
                value_cell.alignment = self._left
            ws.row_dimensions[row].height = 22

        summary_row = start + len(rows) + 1
        ws.merge_cells(start_row=summary_row, start_column=1, end_row=summary_row, end_column=4)
        summary = ws.cell(row=summary_row, column=1, value=log.message or "（无汇总说明）")
        summary.font = _font(size=10, color=_MUTED)
        summary.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True, indent=1)
        summary.fill = _fill("FAFAF9")
        ws.row_dimensions[summary_row].height = 48

        note_row = summary_row + 2
        ws.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=4)
        note = ws.cell(
            row=note_row,
            column=1,
            value="金额为本次计算快照，与报告页一致；明细 Sheet 不作公式回算。",
        )
        note.font = _font(size=9, color=_ACCENT)
        note.alignment = self._indent

    def _write_cards(
        self,
        ws: Worksheet,
        log: AssemblyCostCalcLogVO,
        cards: list[AssemblyCostCalcCardTraceVO],
        filter_text: str,
    ) -> None:
        ws.sheet_properties.tabColor = _ACCENT
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        col_count = len(_CARD_HEADERS)

        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=col_count)
        c1 = ws.cell(row=1, column=1, value="核价卡明细")
        c1.font = _font(size=15, bold=True, color="FFFFFF")
        c1.fill = _fill(_ACCENT)
        c1.alignment = self._indent
        ws.row_dimensions[1].height = 28

        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=col_count)
        c2 = ws.cell(
            row=2,
            column=1,
            value=(
                f"{log.location} / {log.vehicle_model} / {log.bom_version}"
                f"  ·  {log.year}-{log.month:02d}  ·  {filter_text}"
            ),
        )
        c2.font = _font(size=9, color=_MUTED)
        c2.fill = _fill(_CREAM)
        c2.alignment = self._indent
        ws.row_dimensions[2].height = 20

        header_row = 4
        for col, title in enumerate(_CARD_HEADERS, start=1):
            cell = ws.cell(row=header_row, column=col, value=title)
            cell.font = _font(size=9, bold=True, color="FFFFFF")
            cell.alignment = self._center
            cell.border = _thin()
            if col == _KPI_COL:
                cell.fill = _fill(_ACCENT)
            elif col in _MONEY_COLS:
                cell.fill = _fill("BE123C")
            else:
                cell.fill = _fill("44403C")
        ws.row_dimensions[header_row].height = 22

        if not cards:
            empty_row = header_row + 1
            ws.merge_cells(
                start_row=empty_row,
                start_column=1,
                end_row=empty_row,
                end_column=col_count,
            )
            empty = ws.cell(row=empty_row, column=1, value="没有符合筛选的核价卡。")
            empty.font = _font(size=10, color=_MUTED)
            empty.alignment = Alignment(horizontal="center", vertical="center")
            empty.fill = _fill(_PAPER)
            ws.row_dimensions[empty_row].height = 28

        for seq, card in enumerate(cards, start=1):
            row_idx = header_row + seq
            stripe = "FAF7F2" if seq % 2 == 0 else "FFFFFF"
            kpi_fill = "FFF1F2" if seq % 2 == 0 else "FFE4E6"
            values: list[str | int | Decimal] = [
                seq,
                f"L{card.level}",
                "树根" if card.is_tree_root else "",
                card.part_number,
                card.part_name or "",
                card.object_kind or "",
                _STATUS_LABEL.get(card.status, card.status),
                _num(card.material_amount),
                _num(card.welding_amount),
                _num(card.should_cost),
                _num(card.grand_total),
                card.missing_leaf_count,
                card.message or "",
                "；".join(card.missing_parts),
            ]
            for col, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col, value=value)
                cell.border = _thin()
                if col == _KPI_COL:
                    cell.fill = _fill(kpi_fill)
                    cell.font = _font(size=10, bold=True, color=_ACCENT)
                    cell.alignment = self._right
                    cell.number_format = _MONEY_FORMAT
                elif col in _MONEY_COLS:
                    cell.fill = _fill(stripe)
                    cell.font = _font(size=9)
                    cell.alignment = self._right
                    cell.number_format = _MONEY_FORMAT
                elif col == 7:
                    cell.fill = _fill(stripe)
                    cell.font = _font(
                        size=9,
                        bold=True,
                        color=_STATUS_COLOR.get(card.status, _INK),
                    )
                    cell.alignment = self._center
                elif col in {1, 2, 3, 12}:
                    cell.fill = _fill(stripe)
                    cell.font = _font(size=9)
                    cell.alignment = self._center
                else:
                    cell.fill = _fill(stripe)
                    cell.font = _font(size=9, color=_INK)
                    cell.alignment = self._left
            ws.row_dimensions[row_idx].height = 22

        for col, width in enumerate(_CARD_WIDTHS, start=1):
            ws.column_dimensions[get_column_letter(col)].width = width
        ws.freeze_panes = f"A{header_row + 1}"
        last_data_row = header_row + max(len(cards), 1)
        ws.auto_filter.ref = f"A{header_row}:{get_column_letter(col_count)}{last_data_row}"

    def _write_narrative(self, ws: Worksheet, log: AssemblyCostCalcLogVO) -> None:
        ws.sheet_properties.tabColor = "44403C"
        ws.sheet_view.showGridLines = False
        ws.column_dimensions["A"].width = 120
        ws.merge_cells("A1:A1")
        title = ws["A1"]
        title.value = "计算过程说明"
        title.font = _font(size=15, bold=True, color="FFFFFF")
        title.fill = _fill("44403C")
        title.alignment = self._indent
        ws.row_dimensions[1].height = 28

        text = (log.detail_text or "").strip() or "（无过程说明）"
        ws.merge_cells("A3:A3")
        body = ws["A3"]
        body.value = text
        body.font = Font(name="Consolas", size=9, color="44403C")
        body.alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)
        body.fill = _fill(_PAPER)
        line_count = text.count("\n") + 1
        ws.row_dimensions[3].height = min(400, max(80, line_count * 14))
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
