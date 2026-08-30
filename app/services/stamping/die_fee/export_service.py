"""冲压年度模具费 Excel 导出。"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.common.audit import audit_status_label
from app.common.money import Q4, excel_money_cell
from app.common.timezone import now
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException
from app.models.stamping.die_fee_item import StampingDieFeeItem
from app.repositories.stamping.die_fee_repository import StampingDieFeeRepository

_FONT = "微软雅黑"
HEADERS = [
    "序号",
    "年度",
    "基地",
    "项目",
    "零件号",
    "零件名称",
    "生产方式",
    "取价档",
    "单价(万元/吨)",
    "分摊(万台)",
    "系统模具费",
    "调整金额",
    "最终模具费",
    "审核状态",
    "工序序号",
    "工序",
    "预估重量(T)",
    "分摊比例",
    "本序模具费",
    "计算依据",
]
WIDTHS = [6, 8, 10, 12, 16, 18, 12, 10, 14, 12, 14, 12, 14, 10, 10, 12, 14, 10, 14, 40]


def _fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex_color)


def _font(*, size: int = 10, bold: bool = False, color: str = "263238") -> Font:
    return Font(name=_FONT, size=size, bold=bold, color=color)


def _border() -> Border:
    thin = Side(style="thin", color="CFD8DC")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def _num(value: Any) -> Any:
    return excel_money_cell(value, Q4, allow_negative=True)


class StampingDieFeeExportService:
    def __init__(self) -> None:
        self.fee_repo = StampingDieFeeRepository()

    def export(
        self,
        db: Session,
        *,
        year: int,
        location: str,
        vehicle_model: str,
        part_number: str | None,
        audit_status: str | None,
        only_zero: bool,
    ) -> tuple[bytes, str]:
        loc = location.strip()
        vehicle = normalize_vehicle_model(vehicle_model)
        if not loc or not vehicle:
            raise BusinessException("导出必须指定基地和项目")
        rows = self.fee_repo.list_for_export(
            db,
            year=year,
            location=loc,
            vehicle_model=vehicle,
            part_number=part_number,
            audit_status=audit_status,
            only_zero=only_zero,
        )
        workbook = Workbook()
        sheet = workbook.worksheets[0]
        sheet.title = "模具费"
        sheet.append(HEADERS)
        for index, width in enumerate(WIDTHS, start=1):
            sheet.column_dimensions[get_column_letter(index)].width = width
        header_row = sheet[1]
        for cell in header_row:
            cell.font = _font(size=9, bold=True, color="FFFFFF")
            cell.fill = _fill("1A1A22")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = _border()

        seq = 1
        for fee in rows:
            process_rows: list[StampingDieFeeItem | None] = list(fee.items) if fee.items else []
            if not process_rows:
                process_rows = [None]
            for item in process_rows:
                sheet.append(
                    [
                        seq,
                        fee.year,
                        fee.location,
                        fee.vehicle_model,
                        fee.part_number,
                        fee.part_name or "",
                        fee.production_mode or "",
                        "级进模" if fee.price_kind == "progressive" else "钢板模",
                        _num(fee.unit_price),
                        _num(fee.allocation_qty),
                        _num(fee.die_fee),
                        _num(fee.adjustment_amount),
                        _num(fee.final_die_fee),
                        audit_status_label(fee.audit_status),
                        item.process_seq if item is not None else "",
                        item.process_code if item is not None else "",
                        _num(item.estimated_weight_t) if item is not None else "",
                        _num(item.alloc_ratio) if item is not None else "",
                        _num(item.line_die_fee) if item is not None else "",
                        item.basis_text if item is not None else "",
                    ]
                )
            seq += 1

        stamp = now().strftime("%Y%m%d_%H%M%S")
        filename = f"冲压模具费_{year}_{loc}_{vehicle}_{stamp}.xlsx"
        buffer = BytesIO()
        workbook.save(buffer)
        return buffer.getvalue(), filename
