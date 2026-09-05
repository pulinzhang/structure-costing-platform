"""把计算日志写入报告工作簿（不负责 HTTP / 文件名）。"""

from openpyxl import Workbook

from app.common.excel_workbook import resolve_worksheet
from app.schemas.vo.assembly_cost_vo import (
    AssemblyCostCalcCardTraceVO,
    AssemblyCostCalcLogVO,
)
from app.services.costing.assembly_cost.calc_report.cards_sheet import write_cards_sheet
from app.services.costing.assembly_cost.calc_report.columns import (
    CARDS_SHEET,
    COVER_SHEET,
    NARRATIVE_SHEET,
)
from app.services.costing.assembly_cost.calc_report.cover_sheet import write_cover_sheet
from app.services.costing.assembly_cost.calc_report.labels import (
    TreeRootFilter,
    report_filter_text,
)
from app.services.costing.assembly_cost.calc_report.narrative_sheet import (
    write_narrative_sheet,
)


class CalcReportWorkbookBuilder:
    def write(
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
        filter_text = report_filter_text(
            keyword=keyword,
            status=status,
            level=level,
            tree_root=tree_root,
            shown=len(cards),
            total=len(log.cards),
        )
        write_cover_sheet(resolve_worksheet(wb, COVER_SHEET), log, filter_text)
        write_cards_sheet(resolve_worksheet(wb, CARDS_SHEET), log, cards, filter_text)
        write_narrative_sheet(resolve_worksheet(wb, NARRATIVE_SHEET), log)
