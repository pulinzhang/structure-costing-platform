"""协议 Excel 样式（不访问 DB）。"""

from openpyxl.styles import Alignment, Border, Font, Side

THIN = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
META = Alignment(horizontal="left", vertical="center", wrap_text=False)
ANNEX_FONT = Font(name="宋体", size=11)
TITLE_FONT = Font(name="宋体", size=18, bold=True)
BOLD = Font(bold=True)
DATA_ROW_HEIGHT = 22
HEADER_ROW_HEIGHT = 22
TITLE_ROW_HEIGHT = 28
REMARK_LINE_HEIGHT = 18
INT_FORMAT = "0"
PRICE_FORMAT = "0.00"
THOUSANDS_INT_FORMAT = "#,##0"


def agreement_column_widths(month_count: int) -> tuple[float, ...]:
    """按窗口月数给协议表定宽：固定列收紧，结算列随月份加宽。"""
    count = max(int(month_count), 0)
    settlement = 11.0 if count <= 1 else 14.0
    return (
        8.0,
        16.0,
        16.0,
        36.0,
        8.5,
        8.0,
        *([settlement] * count),
        8.0,
        12.0,
        12.0,
        12.0,
        10.0,
    )
