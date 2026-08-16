"""钢材联动价格导出服务（含完整溯源，便于对账扯皮）。"""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sqlalchemy.orm import Session

from app.common.audit import audit_status_label
from app.common.money import Q4, excel_money_cell
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository


logger = logging.getLogger("service.steel_price_export")


def _num(value: Any, quant: Any = Q4, *, allow_negative: bool = True) -> Any:
    return excel_money_cell(value, quant, allow_negative=allow_negative)


def _dt(value: Any) -> Any:
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S") if hasattr(value, "strftime") else str(value)


class SteelPriceExportService:
    """钢材联动价格 Excel 导出。"""

    def __init__(self) -> None:
        self.repository = SteelPriceRepository()

    def export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill: str | None = None,
        audit_status: str | None = None,
    ) -> tuple[bytes, str]:
        """
        生成钢材联动价格 Excel。

        溯源列完整导出（基价 / 厚度 / 宽度 / 锌层：ID + 文件名 + 表页 + 行号 + 列号），
        供对账扯皮核对原始 Excel 单元格。

        Returns:
            (文件字节, 文件名)
        """
        records = self.repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill=steel_mill,
            audit_status=audit_status,
        )

        wb = Workbook()
        ws = wb.worksheets[0]
        ws.title = "钢材联动价格"

        header_font = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        provenance_fill = PatternFill(start_color="C65911", end_color="C65911", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        data_font = Font(name="微软雅黑", size=9, color="000000")
        data_alignment_left = Alignment(horizontal="left", vertical="center")
        data_alignment_right = Alignment(horizontal="right", vertical="center")

        thin_border = Border(
            left=Side(style="thin", color="BFBFBF"),
            right=Side(style="thin", color="BFBFBF"),
            top=Side(style="thin", color="BFBFBF"),
            bottom=Side(style="thin", color="BFBFBF"),
        )

        # 业务列 + 价格列 + 四组溯源 + 计算/审核元数据
        headers = [
            "ID",
            "年度",
            "月份",
            "基地",
            "钢厂",
            "钢种",
            "牌号",
            "厚度(mm)",
            "宽度(mm)",
            "规格",
            "基准价",
            "厚度加减价",
            "宽度加减价",
            "锌层加减价",
            "加工费",
            "其他调整",
            "最终价/吨",
            # 基价溯源
            "基价ID",
            "基价文件名",
            "基价表页",
            "基价行号",
            "基价列号",
            # 厚度溯源
            "厚度政策ID",
            "厚度阶梯ID",
            "厚度文件名",
            "厚度表页",
            "厚度行号",
            "厚度列号",
            # 宽度溯源
            "宽度政策ID",
            "宽度阶梯ID",
            "宽度文件名",
            "宽度表页",
            "宽度行号",
            "宽度列号",
            # 锌层溯源
            "锌层政策ID",
            "锌层阶梯ID",
            "锌层文件名",
            "锌层表页",
            "锌层行号",
            "锌层列号",
            # 计算 / 审核
            "匹配状态",
            "计算状态",
            "计算说明",
            "计算批次",
            "公式版本",
            "计算时间",
            "审核状态",
            "审核人",
            "审核时间",
            "审核意见",
            "反审核人",
            "反审核时间",
            "反审核原因",
            "备注",
            # 审计（扯皮核对）
            "创建人",
            "创建时间",
            "最后修改人",
            "最后修改时间",
        ]

        # 溯源列区间（1-based）：基价 18-22，厚度 23-28，宽度 29-34，锌层 35-40
        provenance_cols = set(range(18, 41))

        ws.append(headers)
        ws.row_dimensions[1].height = 32
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = provenance_fill if col_idx in provenance_cols else header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        right_align_cols = {
            1, 2, 3, 8, 9, 11, 12, 13, 14, 15, 16, 17,
            18, 21, 22, 23, 24, 27, 28, 29, 30, 33, 34, 35, 36, 39, 40,
        }

        for row_idx, record in enumerate(records, start=2):
            row_data = [
                record.id,
                record.year,
                record.month,
                record.location or "",
                record.steel_mill or "",
                record.category_name or "",
                record.grade or "",
                _num(record.thickness, Q4),
                _num(record.width, Q4),
                record.spec or "",
                _num(record.base_price, Q4),
                _num(record.thickness_adjustment, Q4, allow_negative=True),
                _num(record.width_adjustment, Q4, allow_negative=True),
                _num(record.zinc_adjustment, Q4, allow_negative=True),
                _num(record.processing_fee, Q4),
                _num(record.other_adjustment, Q4, allow_negative=True),
                _num(record.final_price_per_ton, Q4),
                # 基价溯源
                record.base_price_id or "",
                record.base_excel_filename or "",
                record.base_sheet_name or "",
                record.base_excel_row if record.base_excel_row is not None else "",
                record.base_excel_col if record.base_excel_col is not None else "",
                # 厚度溯源
                record.thickness_policy_id or "",
                record.thickness_ladder_item_id or "",
                record.thickness_excel_filename or "",
                record.thickness_sheet_name or "",
                record.thickness_excel_row if record.thickness_excel_row is not None else "",
                record.thickness_excel_col if record.thickness_excel_col is not None else "",
                # 宽度溯源
                record.width_policy_id or "",
                record.width_ladder_item_id or "",
                record.width_excel_filename or "",
                record.width_sheet_name or "",
                record.width_excel_row if record.width_excel_row is not None else "",
                record.width_excel_col if record.width_excel_col is not None else "",
                # 锌层溯源
                record.zinc_policy_id or "",
                record.zinc_ladder_item_id or "",
                record.zinc_excel_filename or "",
                record.zinc_sheet_name or "",
                record.zinc_excel_row if record.zinc_excel_row is not None else "",
                record.zinc_excel_col if record.zinc_excel_col is not None else "",
                # 计算 / 审核
                record.match_status or "",
                record.calc_status or "",
                record.calc_message or "",
                record.calc_batch_id or "",
                record.formula_version or "",
                _dt(record.calculated_at),
                audit_status_label(record.audit_status),
                record.audited_by or "",
                _dt(record.audited_at),
                record.audit_remark or "",
                record.reverse_audited_by or "",
                _dt(record.reverse_audited_at),
                record.reverse_audit_remark or "",
                record.remark or "",
                # 审计
                record.created_by or "",
                _dt(record.created_at),
                record.updated_by or "",
                _dt(record.updated_at),
            ]
            ws.append(row_data)

            fill = PatternFill(
                start_color="F2F2F2" if row_idx % 2 == 0 else "FFFFFF",
                end_color="F2F2F2" if row_idx % 2 == 0 else "FFFFFF",
                fill_type="solid",
            )
            for col_idx in range(1, len(row_data) + 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font = data_font
                cell.border = thin_border
                cell.fill = fill
                cell.alignment = (
                    data_alignment_right if col_idx in right_align_cols else data_alignment_left
                )

        column_widths = [
            8, 8, 8, 10, 10, 8, 16, 10, 10, 14,
            12, 12, 12, 12, 10, 10, 12,
            10, 28, 12, 10, 10,
            12, 12, 28, 12, 10, 10,
            12, 12, 28, 12, 10, 10,
            12, 12, 28, 12, 10, 10,
            14, 10, 24, 20, 10, 18,
            10, 10, 18, 16, 10, 18, 16, 20,
            12, 18, 12, 18,
        ]
        for col_idx, width in enumerate(column_widths, start=1):
            letter = ws.cell(row=1, column=col_idx).column_letter
            ws.column_dimensions[letter].width = width

        ws.freeze_panes = "A2"

        parts = ["钢材联动价格导出"]
        if year:
            parts.append(f"{year}年")
        if month:
            parts.append(f"{month}月")
        if location:
            parts.append(location)
        if category_name:
            parts.append(category_name)
        if steel_mill:
            parts.append(steel_mill)
        if grade:
            parts.append(grade)
        if audit_status:
            parts.append(audit_status_label(audit_status))
        filename = "_".join(parts) + ".xlsx"

        output = BytesIO()
        wb.save(output)
        logger.info(
            "导出钢材联动价格 Excel 完成: filename=%s records=%d",
            filename,
            len(records),
        )
        return output.getvalue(), filename
