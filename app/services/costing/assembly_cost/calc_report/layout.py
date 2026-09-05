"""计算报告页打印与页签色。"""

from openpyxl.worksheet.worksheet import Worksheet


def apply_report_page(
    ws: Worksheet,
    *,
    tab_color: str,
    fit_height: int,
    landscape: bool = True,
    show_grid: bool | None = False,
) -> None:
    ws.sheet_properties.tabColor = tab_color
    if landscape:
        ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = fit_height
    if show_grid is not None:
        ws.sheet_view.showGridLines = show_grid
