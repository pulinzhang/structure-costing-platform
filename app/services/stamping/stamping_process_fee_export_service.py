"""冲压加工费 Excel 导出服务。"""

from __future__ import annotations

import logging
from datetime import datetime
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sqlalchemy.orm import Session

from app.common.audit import audit_status_label
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)


logger = logging.getLogger("service.stamping_process_fee_export")



def _num(value: Any, digits: int | None = None):
    if value is None:
        return ""
    number = float(value)
    if digits is None:
        return number
    return round(number, digits)


def _dt(value: Any) -> str:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S") if hasattr(value, "strftime") else str(value)


def _format_process_basis_column(record: Any) -> str:
    """多工序溯源合并为一列（换行分隔）。"""
    items = list(getattr(record, "process_items", None) or [])
    if not items:
        return ""
    items = sorted(
        items,
        key=lambda item: (
            item.process_order if item.process_order is not None else 10**9,
            item.id or 0,
        ),
    )
    lines: list[str] = []
    for item in items:
        text = (item.basis_text or "").strip()
        if text:
            lines.append(text)
            continue
        seq = (item.process_seq or "").strip() or "?"
        code = (item.process_code or "").strip()
        label = f"{seq}/{code}" if code else seq
        fee = _num(item.line_fee, 3)
        lines.append(f"{label}: {fee}")
    return "\n".join(lines)


class StampingProcessFeeExportService:
    """冲压加工费 Excel 导出。"""

    def __init__(self) -> None:
        self.repository = StampingProcessFeeRepository()

    def export(
        self,
        db: Session,
        *,
        year: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
        part_number: str | None = None,
        audit_status: str | None = None,
    ) -> tuple[bytes, str]:
        records = self.repository.list_for_export(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
            version=version,
            part_number=part_number,
            audit_status=audit_status,
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "冲压加工费"

        header_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        data_font = Font(name="微软雅黑", size=9, color="000000")
        align_left = Alignment(horizontal="left", vertical="center")
        align_right = Alignment(horizontal="right", vertical="center")
        thin_border = Border(
            left=Side(style="thin", color="BFBFBF"),
            right=Side(style="thin", color="BFBFBF"),
            top=Side(style="thin", color="BFBFBF"),
            bottom=Side(style="thin", color="BFBFBF"),
        )

        headers = [
            "ID",
            "年度",
            "基地",
            "冲压工厂",
            "车型",
            "版本",
            "序号",
            "零件号",
            "零件名称",
            "材质",
            "料厚",
            "零件重量",
            "料片长",
            "料片宽",
            "可制件数",
            "板料类型",
            "模具类型",
            "工艺方法",
            "自动化",
            "零件备注",
            "来源文件",
            "工序数",
            "系统计算加工费",
            "手工调整单价",
            "最终加工费",
            "工序单价溯源",
            "计算失败原因",
            "备注",
            "审核状态",
            "审核人",
            "审核时间",
            "审核意见",
            "反审核人",
            "反审核时间",
            "反审核意见",
            "创建人",
            "创建时间",
            "修改人",
            "修改时间",
        ]

        for col, title in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=title)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        for row_idx, record in enumerate(records, start=2):
            values = [
                record.id,
                record.year,
                record.location,
                record.stamping_supplier,
                record.vehicle_model,
                record.version,
                record.seq_no,
                record.part_number,
                record.part_name,
                record.material,
                _num(record.thickness, 4),
                _num(record.part_weight, 4),
                _num(record.sheet_length, 2),
                _num(record.sheet_width, 2),
                record.parts_per_sheet,
                record.sheet_type,
                record.die_type,
                record.process_method,
                record.automation,
                record.part_remark,
                record.excel_filename,
                record.process_count,
                _num(record.processing_fee, 3),
                _num(record.manual_unit_price, 3),
                _num(record.final_processing_fee, 3),
                _format_process_basis_column(record),
                record.calc_fail_reason,
                record.remark,
                audit_status_label(record.audit_status),
                record.audited_by,
                _dt(record.audited_at),
                record.audit_remark,
                record.reverse_audited_by,
                _dt(record.reverse_audited_at),
                record.reverse_audit_remark,
                record.created_by,
                _dt(record.created_at),
                record.updated_by,
                _dt(record.updated_at),
            ]
            for col, value in enumerate(values, start=1):
                cell = ws.cell(row=row_idx, column=col, value="" if value is None else value)
                cell.font = data_font
                cell.border = thin_border
                if col == 26:
                    cell.alignment = Alignment(
                        horizontal="left", vertical="center", wrap_text=True
                    )
                else:
                    cell.alignment = (
                        align_right
                        if col in {1, 2, 7, 11, 12, 13, 14, 15, 22, 23, 24, 25}
                        else align_left
                    )

        for col in range(1, len(headers) + 1):
            letter = ws.cell(row=1, column=col).column_letter
            ws.column_dimensions[letter].width = 36 if col == 26 else 14
        ws.freeze_panes = "A2"

        buffer = BytesIO()
        wb.save(buffer)
        content = buffer.getvalue()

        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts = ["冲压加工费"]
        if year:
            parts.append(f"{year}年")
        if location:
            parts.append(location)
        if stamping_supplier:
            parts.append(stamping_supplier)
        filename = "_".join(parts) + f"_{stamp}.xlsx"
        logger.info("导出冲压加工费 %s 条 -> %s", len(records), filename)
        return content, filename
