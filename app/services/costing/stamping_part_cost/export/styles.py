"""导出共用 openpyxl 样式。"""

from openpyxl.styles import Border, Font, PatternFill, Side

THIN_BORDER = Border(
    left=Side(style="thin", color="333333"),
    right=Side(style="thin", color="333333"),
    top=Side(style="thin", color="333333"),
    bottom=Side(style="thin", color="333333"),
)

WEAK_HEADER_FILL = PatternFill("solid", fgColor="455A64")
WEAK_HEADER_FONT = Font(name="微软雅黑", size=8, bold=True, color="B0BEC5")
WEAK_DATA_FONT = Font(name="微软雅黑", size=8, color="9E9E9E")
