"""
钢价政策 Excel 导出器
职责：纯 Excel 生成逻辑，不涉及数据库操作
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from app.common.export_watermark import workbook_to_xlsx_bytes
from app.common.money import Q2, format_money
from app.repositories.yishiyiyi.policy.dto import ExportRow
from app.schemas.vo.user_vo import UserVO


# =============================================================================
# 样式常量
# =============================================================================

HEADER_FONT = Font(name="微软雅黑", size=10, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")

DATA_FONT = Font(name="微软雅黑", size=10, color="000000")
DATA_ALIGNMENT = Alignment(horizontal="left", vertical="center")
DATA_ALIGNMENT_CENTER = Alignment(horizontal="center", vertical="center")
DATA_ALIGNMENT_RIGHT = Alignment(horizontal="right", vertical="center")

THIN_BORDER = Border(
    left=Side(style="thin", color="BFBFBF"),
    right=Side(style="thin", color="BFBFBF"),
    top=Side(style="thin", color="BFBFBF"),
    bottom=Side(style="thin", color="BFBFBF"),
)

EVEN_FILL = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
ODD_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")

HEADERS = [
    "政策ID",
    "年度",
    "月份",
    "钢厂",
    "钢种大类",
    "政策类型",
    "牌号类型",
    "牌号/范围",
    "基准厚度",
    "明细ID",
    "子分组",
    "厚度条件",
    "宽度条件",
    "锌层条件",
    "加减价(元/吨)",
    "基准",
    "排序",
    "文件名",
    "行号",
    "列号",
]

COLUMN_WIDTHS = [10, 8, 8, 12, 12, 12, 10, 15, 10, 10, 15, 18, 18, 14, 8, 8, 30, 8, 8]


# =============================================================================
# 格式化辅助函数
# =============================================================================


def format_decimal(value: Any, digits: Any = 2) -> str:
    if value is None:
        return ""
    places = int(digits) if digits is not None else 2
    quant = Q2 if places == 2 else Decimal(10) ** -places
    try:
        return format_money(value, quant, places, allow_negative=True)
    except (InvalidOperation, ValueError, TypeError):
        return value if isinstance(value, str) else str(value)


def format_interval(
    variable: str,
    min_val: Any,
    min_op: str | None,
    max_val: Any,
    max_op: str | None,
    decimals: int = 2,
) -> str:
    """
    通用区间格式化函数（数学区间写法，如 2.0 ≤ t ≤ 5.0）

    Args:
        variable: 变量名，如 't'、'w'
        min_val: 最小值（number 或 None）
        min_op:  最小值运算符，'>=' 或 '>'
        max_val: 最大值（number 或 None）
        max_op:  最大值运算符，'<=' 或 '<'
        decimals: 小数位数

    Returns:
        格式化后的条件字符串
    """

    def fmt(v: Any) -> Any:
        if v is None:
            return ""
        return format_decimal(v, decimals)

    def min_symbol(op: str | None) -> str:
        if op == ">=":
            return "≤"
        if op == ">":
            return "<"
        return ""

    def max_symbol(op: str | None) -> str:
        if op == "<=":
            return "≤"
        if op == "<":
            return "<"
        return ""

    has_min = min_val is not None and min_op
    has_max = max_val is not None and max_op

    # 两者都有：2.0 ≤ t ≤ 5.0
    if has_min and has_max:
        return f"{fmt(min_val)} {min_symbol(min_op)} {variable} {max_symbol(max_op)} {fmt(max_val)}"

    # 只有下限：2.0 ≤ t
    if has_min:
        return f"{fmt(min_val)} {min_symbol(min_op)} {variable}"

    # 只有上限：t ≤ 5.0
    if has_max:
        return f"{variable} {max_symbol(max_op)} {fmt(max_val)}"

    return "-"


def format_thick_condition(row: ExportRow) -> str:
    return format_interval(
        "t",
        row.thick_min,
        row.thick_min_operator,
        row.thick_max,
        row.thick_max_operator,
        decimals=2,
    )


def format_width_condition(row: ExportRow) -> str:
    return format_interval(
        "w",
        row.width_min,
        row.width_min_operator,
        row.width_max,
        row.width_max_operator,
        decimals=0,
    )


def format_zinc_condition(row: ExportRow) -> str:
    return format_interval(
        "z",
        row.zinc_coating_min,
        row.zinc_coating_min_operator,
        row.zinc_coating_max,
        row.zinc_coating_max_operator,
        decimals=0,
    )


# =============================================================================
# 导出器类
# =============================================================================


class SteelPricePolicyExporter:
    """钢价政策 Excel 导出器"""

    def generate(
        self,
        records: list[ExportRow],
        *,
        current_user: UserVO,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
    ) -> tuple[bytes, str]:
        """
        生成 Excel 文件字节数据。
        返回 (文件字节数据, 文件名)
        """
        wb = Workbook()
        ws = wb.worksheets[0]
        ws.title = "厚度加减价导出"

        self._write_headers(ws)
        self._write_rows(ws, records)
        self._set_column_widths(ws)
        ws.freeze_panes = "A2"

        filename = self._build_filename(year, month, steel_mill)
        content = workbook_to_xlsx_bytes(wb, current_user)
        return content, filename

    def _write_headers(self, ws: Any) -> None:
        """写入表头行"""
        ws.append(HEADERS)
        for col_idx, _ in enumerate(HEADERS, start=1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = HEADER_FONT
            cell.fill = HEADER_FILL
            cell.alignment = HEADER_ALIGNMENT
            cell.border = THIN_BORDER

    def _write_rows(self, ws: Any, records: list[ExportRow]) -> None:
        """写入数据行"""
        for row_idx, row in enumerate(records, start=2):
            row_data = [
                row.policy_id or "",
                row.year or "",
                row.month or "",
                row.steel_mill or "",
                row.category_name or "",
                row.policy_type or "",
                row.grade_type or "",
                row.grade_value or "",
                format_decimal(row.base_thickness),
                row.item_id or "",
                row.target_sub_group or "",
                format_thick_condition(row),
                format_width_condition(row),
                format_zinc_condition(row),
                row.price_adjustment if row.price_adjustment is not None else "",
                "是" if row.is_base == 1 else "",
                row.sort_order or 0,
                row.excel_filename or "",
                row.excel_row or "",
                row.excel_col or "",
            ]
            ws.append(row_data)

            fill = EVEN_FILL if row_idx % 2 == 0 else ODD_FILL
            for col_idx, _ in enumerate(row_data, start=1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font = DATA_FONT
                cell.border = THIN_BORDER
                cell.fill = fill
                if col_idx in (1, 2, 3, 10, 17, 18, 19):
                    cell.alignment = DATA_ALIGNMENT_RIGHT
                elif col_idx in (14,):
                    cell.alignment = DATA_ALIGNMENT_CENTER
                else:
                    cell.alignment = DATA_ALIGNMENT

    def _set_column_widths(self, ws: Any) -> None:
        """设置列宽"""
        for col_idx, width in enumerate(COLUMN_WIDTHS, start=1):
            letter = ws.cell(row=1, column=col_idx).column_letter
            ws.column_dimensions[letter].width = width

    def _build_filename(
        self,
        year: int | None,
        month: int | None,
        steel_mill: str | None,
    ) -> str:
        """构建导出文件名"""
        parts = ["厚度加减价导出"]
        if year:
            parts.append(f"{year}年")
        if month:
            parts.append(f"{month}月")
        if steel_mill:
            parts.append(steel_mill)
        return f"{'_'.join(parts)}.xlsx"
