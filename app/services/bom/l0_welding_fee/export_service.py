"""BOM 成品焊接费 Excel 导出（核对风排版）。"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.common.audit import audit_status_label
from app.common.excel_workbook import resolve_worksheet
from app.common.export_filters import require_at_least_one_export_filter
from app.common.money import Q4, excel_money_cell
from app.common.timezone import now
from app.models.bom import BomL0WeldingFee
from app.repositories.bom.l0_welding_fee_repository import BomL0WeldingFeeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)

logger = logging.getLogger("service.bom.l0_welding_fee.export")

_FONT = "微软雅黑"

_MATCH_LABEL = {
    "matched": "已匹配",
    "missing_price": "缺单价",
    "unmapped": "未映射",
}
_CALC_LABEL = {
    "ok": "正常",
    "partial": "缺单价",
    "failed": "失败",
}

# 主表列（纵向合并）+ 明细分隔
MAIN_COLS = 17
COL_COUNT = 24
HEADERS = [
    "序号",
    "年度",
    "基地",
    "项目",
    "版本",
    "零件号",
    "零件名称",
    "焊接信息原文",
    "工艺数",
    "命中",
    "缺单价",
    "系统计算",
    "其它费用",
    "确认单价",
    "备注",
    "计算状态",
    "审核状态",
    "标准工艺",
    "过程量",
    "过程量单位",
    "单价",
    "单价单位",
    "行费",
    "匹配状态",
]
WIDTHS = [
    6,
    8,
    10,
    10,
    10,
    16,
    18,
    36,
    8,
    8,
    8,
    14,
    12,
    14,
    24,
    10,
    10,
    18,
    10,
    10,
    10,
    10,
    10,
    10,
]

TITLE_H = 28
FILTER_H = 20
NOTE_H = 20
GROUP_H = 18
HEADER_H = 22
DATA_H = 26


def _fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex_color)


def _font(*, size: int = 10, bold: bool = False, color: str = "263238") -> Font:
    return Font(name=_FONT, size=size, bold=bold, color=color)


def _border(*, right: Side | None = None, left: Side | None = None) -> Border:
    thin = Side(style="thin", color="CFD8DC")
    return Border(
        left=left or thin,
        right=right or thin,
        top=thin,
        bottom=thin,
    )


def _num(value: Any) -> Any:
    return excel_money_cell(value, Q4)


class BomL0WeldingFeeExportService:
    """按筛选导出成品焊接费（主表合并 + 工艺明细分行）。"""

    def __init__(self) -> None:
        self.fee_repo = BomL0WeldingFeeRepository()
        self.breakdown_repo = BomWeldingProcessBreakdownRepository()
        self._left = Alignment(horizontal="left", vertical="center", wrap_text=True)
        self._center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        self._right = Alignment(horizontal="right", vertical="center")
        self._thin = _border()
        self._split_main = _border(right=Side(style="medium", color="B71C1C"))
        self._split_detail = _border(left=Side(style="medium", color="B71C1C"))

    def write_to_workbook(
        self,
        wb: Workbook,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
        sheet_title: str = "成品焊接费",
    ) -> tuple[str, int]:
        records = self.fee_repo.list_for_export(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
        )
        self._fill_missing_weld_info(db, records)

        ws = resolve_worksheet(wb, sheet_title)

        filter_text = self._filter_text(
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
        )
        self._write_banner(ws, filter_text=filter_text, fee_count=len(records))
        header_row = self._write_headers(ws)

        row_idx = header_row + 1
        for seq_no, record in enumerate(records, start=1):
            items = sorted(
                list(record.items or []),
                key=lambda item: (item.line_no or 0, item.id or 0),
            )
            main_fill = _fill("ECEFF1") if seq_no % 2 else _fill("F5F7FA")
            if not items:
                self._write_data_row(
                    ws,
                    row_idx,
                    record,
                    seq_no=seq_no,
                    item=None,
                    write_main=True,
                    line_index=0,
                    main_fill=main_fill,
                )
                ws.row_dimensions[row_idx].height = self._row_height(record)
                row_idx += 1
                continue

            group_start = row_idx
            for i, item in enumerate(items):
                self._write_data_row(
                    ws,
                    row_idx,
                    record,
                    seq_no=seq_no,
                    item=item,
                    write_main=(i == 0),
                    line_index=i,
                    main_fill=main_fill,
                )
                ws.row_dimensions[row_idx].height = self._row_height(record)
                row_idx += 1
            if row_idx - 1 > group_start:
                self._merge_main(ws, group_start, row_idx - 1, main_fill)

        last_data = max(header_row, row_idx - 1)
        for idx, width in enumerate(WIDTHS, start=1):
            ws.column_dimensions[get_column_letter(idx)].width = width

        ws.freeze_panes = f"A{header_row + 1}"
        ws.auto_filter.ref = f"A{header_row}:{get_column_letter(COL_COUNT)}{last_data}"
        ws.print_title_rows = f"1:{header_row}"
        ws.page_setup.orientation = "landscape"
        ws.page_setup.fitToPage = True
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.page_margins.left = 0.3
        ws.page_margins.right = 0.3
        ws.page_margins.top = 0.35
        ws.page_margins.bottom = 0.35
        ws.sheet_view.showGridLines = False
        ws.sheet_view.zoomScale = 90

        return ws.title, len(records)

    def export(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        bom_version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
        calc_status: str | None = None,
    ) -> tuple[bytes, str]:
        require_at_least_one_export_filter(
            year,
            location,
            vehicle_model,
            bom_version,
            part_number,
            audit_status,
            calc_status,
        )
        wb = Workbook()
        _title, fee_count = self.write_to_workbook(
            wb,
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            part_number=part_number,
            audit_status=audit_status,
            calc_status=calc_status,
        )
        # header_row is always 5 (banner 1–3 + group 4 + headers 5)
        export_row_count = max(0, wb.worksheets[0].max_row - 5)

        buffer = BytesIO()
        wb.save(buffer)
        content = buffer.getvalue()

        scope_parts = [
            str(year) if year else None,
            location,
            vehicle_model,
            bom_version,
        ]
        scope = "_".join(p for p in scope_parts if p) or "全部"
        stamp = now().strftime("%Y%m%d_%H%M%S")
        filename = f"成品焊接费_{scope}_{stamp}.xlsx"
        logger.info(
            "导出成品焊接费 %s 条主表 / %s 行明细 / 文件 %s",
            fee_count,
            export_row_count,
            filename,
        )
        return content, filename

    def _write_banner(self, ws: Any, *, filter_text: str, fee_count: int) -> None:
        indent = Alignment(horizontal="left", vertical="center", indent=1)

        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=COL_COUNT)
        c1 = ws.cell(row=1, column=1, value="成品焊接费核对表")
        c1.font = _font(size=15, bold=True, color="FFFFFF")
        c1.fill = _fill("1A237E")
        c1.alignment = indent
        ws.row_dimensions[1].height = TITLE_H

        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=COL_COUNT)
        c2 = ws.cell(
            row=2,
            column=1,
            value=(
                f"{filter_text} · 共 {fee_count} 个成品"
                f"　　导出 {now().strftime('%Y-%m-%d %H:%M')}"
            ),
        )
        c2.font = _font(size=9, color="455A64")
        c2.fill = _fill("E8EAF6")
        c2.alignment = indent
        ws.row_dimensions[2].height = FILTER_H

        ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=COL_COUNT)
        c3 = ws.cell(
            row=3,
            column=1,
            value="说明：左侧主表按成品合并；右侧为工艺明细。行费 = 计费量 × 分年单价；仅成品计费。",
        )
        c3.font = _font(size=9, color="B71C1C")
        c3.fill = _fill("FFF3E0")
        c3.alignment = indent
        ws.row_dimensions[3].height = NOTE_H

    def _write_headers(self, ws: Any) -> int:
        group_row = 4
        header_row = 5
        white = _font(size=9, bold=True, color="FFFFFF")
        header_font = _font(bold=True, color="FFFFFF")

        ws.merge_cells(
            start_row=group_row,
            start_column=1,
            end_row=group_row,
            end_column=MAIN_COLS,
        )
        ws.merge_cells(
            start_row=group_row,
            start_column=MAIN_COLS + 1,
            end_row=group_row,
            end_column=COL_COUNT,
        )
        main_group = ws.cell(row=group_row, column=1, value="成品主表")
        main_group.font = white
        main_group.fill = _fill("37474F")
        main_group.alignment = self._center
        for col in range(1, MAIN_COLS + 1):
            cell = ws.cell(row=group_row, column=col)
            cell.fill = _fill("37474F")
            cell.border = self._thin if col < MAIN_COLS else self._split_main

        detail_group = ws.cell(row=group_row, column=MAIN_COLS + 1, value="工艺明细 / 计费")
        detail_group.font = white
        detail_group.fill = _fill("B71C1C")
        detail_group.alignment = self._center
        for col in range(MAIN_COLS + 1, COL_COUNT + 1):
            cell = ws.cell(row=group_row, column=col)
            cell.fill = _fill("B71C1C")
            cell.border = self._split_detail if col == MAIN_COLS + 1 else self._thin
        ws.row_dimensions[group_row].height = GROUP_H

        fee_cols = {12, 13, 14, 23}  # 系统计算、其它费用、确认单价、行费
        for col, title in enumerate(HEADERS, start=1):
            cell = ws.cell(row=header_row, column=col, value=title)
            cell.font = header_font
            cell.alignment = self._center
            if col <= MAIN_COLS:
                cell.fill = _fill("EF6C00") if col in fee_cols else _fill("546E7A")
                cell.border = self._thin if col < MAIN_COLS else self._split_main
            elif col in fee_cols:
                cell.fill = _fill("EF6C00")
                cell.border = self._thin
            else:
                cell.fill = _fill("C62828")
                cell.border = self._split_detail if col == MAIN_COLS + 1 else self._thin
        ws.row_dimensions[header_row].height = HEADER_H
        return header_row

    def _write_data_row(
        self,
        ws: Any,
        row_idx: int,
        record: BomL0WeldingFee,
        *,
        seq_no: int,
        item: Any,
        write_main: bool,
        line_index: int,
        main_fill: PatternFill,
    ) -> None:
        detail_fill = _fill("FFFFFF") if line_index % 2 == 0 else _fill("FFEBEE")
        missing = int(record.missing_price_count or 0) > 0
        calc_status = record.calc_status or ""
        match_status = (item.match_status if item else "") or ""

        if write_main:
            main_values: list[Any] = [
                seq_no,
                record.year,
                record.location,
                record.vehicle_model,
                record.bom_version,
                record.part_number,
                record.part_name or "",
                (record.weld_info_raw or "").strip(),
                record.process_line_count,
                record.matched_line_count,
                record.missing_price_count,
                _num(record.total_l0_welding_fee),
                _num(record.other_fee),
                _num(record.final_l0_welding_fee),
                (record.remark or "").strip(),
                _CALC_LABEL.get(calc_status, calc_status),
                audit_status_label(record.audit_status),
            ]
            for col, value in enumerate(main_values, start=1):
                cell = ws.cell(row=row_idx, column=col, value="" if value is None else value)
                cell.fill = main_fill
                cell.border = self._thin if col < MAIN_COLS else self._split_main
                if col == 1:
                    cell.font = _font(size=11, bold=True, color="37474F")
                    cell.alignment = self._center
                elif col == 6:
                    cell.font = _font(bold=True, color="1565C0")
                    cell.alignment = self._left
                elif col == 8:
                    cell.font = _font(size=9, color="607D8B")
                    cell.alignment = self._left
                elif col == 12:
                    cell.font = _font(size=11, bold=True, color="546E7A")
                    cell.alignment = self._right
                elif col == 13:
                    cell.font = _font(size=11, color="37474F")
                    cell.alignment = self._right
                elif col == 14:
                    cell.font = _font(size=11, bold=True, color="E65100")
                    cell.alignment = self._right
                    cell.fill = _fill("FFF3E0")
                elif col == 15:
                    cell.font = _font(size=9, color="607D8B")
                    cell.alignment = self._left
                elif col in {9, 10, 11}:
                    cell.font = (
                        _font(bold=True, color="C62828") if (col == 11 and missing) else _font()
                    )
                    cell.alignment = self._center
                elif col == 16:
                    cell.font, cell.fill = self._status_tone(calc_status)
                    cell.alignment = self._center
                elif col == 17:
                    cell.font, cell.fill = self._audit_tone(record.audit_status)
                    cell.alignment = self._center
                else:
                    cell.font = _font()
                    cell.alignment = self._left if col in {3, 4, 5, 7, 15} else self._center

        detail_values: list[Any] = [
            (item.standard_process_name or item.process_token or "") if item else "",
            _num(item.process_qty) if item else "",
            (item.process_qty_unit or "") if item else "",
            _num(item.unit_price) if item and item.unit_price is not None else "",
            (item.unit or "") if item else "",
            _num(item.line_fee) if item and item.line_fee is not None else "",
            _MATCH_LABEL.get(match_status, match_status) if item else "",
        ]
        for offset, value in enumerate(detail_values):
            col = MAIN_COLS + 1 + offset
            cell = ws.cell(row=row_idx, column=col, value="" if value is None else value)
            cell.fill = detail_fill
            cell.border = self._split_detail if col == MAIN_COLS + 1 else self._thin
            if col == 20:  # 行费
                cell.font = _font(size=11, bold=True, color="E65100")
                cell.alignment = self._right
                cell.fill = _fill("FFF3E0")
            elif col in {16, 18}:
                cell.font = _font()
                cell.alignment = self._right
            elif col == 21:
                cell.font, cell.fill = self._match_tone(match_status)
                cell.alignment = self._center
            else:
                cell.font = _font()
                cell.alignment = self._left if col == 15 else self._center

    def _merge_main(
        self,
        ws: Any,
        start_row: int,
        end_row: int,
        main_fill: PatternFill,
    ) -> None:
        for col in range(1, MAIN_COLS + 1):
            ws.merge_cells(
                start_row=start_row,
                start_column=col,
                end_row=end_row,
                end_column=col,
            )
            cell = ws.cell(row=start_row, column=col)
            if col == 12:
                cell.fill = _fill("FFF3E0")
            else:
                cell.fill = main_fill
            cell.border = self._thin if col < MAIN_COLS else self._split_main

    @staticmethod
    def _row_height(record: BomL0WeldingFee) -> float:
        weld = (record.weld_info_raw or "").strip()
        extra = 0.0
        if len(weld) > 40:
            extra = min(36.0, (len(weld) // 40) * 8.0)
        return DATA_H + extra

    @staticmethod
    def _status_tone(calc_status: str) -> tuple[Font, PatternFill]:
        if calc_status == "ok":
            return _font(bold=True, color="2E7D32"), _fill("E8F5E9")
        if calc_status == "partial":
            return _font(bold=True, color="EF6C00"), _fill("FFF3E0")
        if calc_status == "failed":
            return _font(bold=True, color="C62828"), _fill("FFEBEE")
        return _font(), _fill("FFFFFF")

    @staticmethod
    def _audit_tone(audit_status: str | None) -> tuple[Font, PatternFill]:
        if audit_status == "approved":
            return _font(bold=True, color="2E7D32"), _fill("E8F5E9")
        if audit_status == "pending":
            return _font(bold=True, color="EF6C00"), _fill("FFF8E1")
        if audit_status == "rejected":
            return _font(bold=True, color="C62828"), _fill("FFEBEE")
        return _font(), _fill("FFFFFF")

    @staticmethod
    def _match_tone(match_status: str) -> tuple[Font, PatternFill]:
        if match_status == "matched":
            return _font(bold=True, color="2E7D32"), _fill("E8F5E9")
        if match_status == "missing_price":
            return _font(bold=True, color="EF6C00"), _fill("FFF3E0")
        if match_status == "unmapped":
            return _font(bold=True, color="607D8B"), _fill("ECEFF1")
        return _font(), _fill("FFFFFF")

    @staticmethod
    def _filter_text(
        *,
        year: int | None,
        location: str | None,
        vehicle_model: str | None,
        bom_version: str | None,
        part_number: str | None,
        audit_status: str | None,
        calc_status: str | None,
    ) -> str:
        parts: list[str] = []
        if year is not None:
            parts.append(f"年度={year}")
        if location:
            parts.append(f"基地={location}")
        if vehicle_model:
            parts.append(f"项目={vehicle_model}")
        if bom_version:
            parts.append(f"版本={bom_version}")
        if part_number:
            parts.append(f"零件号含={part_number}")
        if audit_status:
            parts.append(f"审核={audit_status_label(audit_status)}")
        if calc_status:
            parts.append(f"计算={_CALC_LABEL.get(calc_status, calc_status)}")
        return " · ".join(parts) if parts else "全部筛选"

    def _fill_missing_weld_info(self, db: Session, records: list[BomL0WeldingFee]) -> None:
        need_ids = [
            int(r.source_breakdown_node_id)
            for r in records
            if r.source_breakdown_node_id and not (r.weld_info_raw or "").strip()
        ]
        if not need_ids:
            return
        weld_map = self.breakdown_repo.map_weld_info_by_ids(db, need_ids)
        for record in records:
            if (record.weld_info_raw or "").strip():
                continue
            node_id = record.source_breakdown_node_id
            if not node_id:
                continue
            text = weld_map.get(int(node_id))
            if text:
                record.weld_info_raw = text
