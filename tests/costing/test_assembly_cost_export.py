"""成品核价导出：零件短码列。"""

from app.services.costing.assembly_cost.export.assembly_cost_export_service import (
    LIST_HEADERS,
    LIST_KPI_COL,
    LIST_MONEY_COLS,
    part_short_code,
)


def test_short_code_column_after_part_number() -> None:
    assert LIST_HEADERS[4] == "零件号"
    assert LIST_HEADERS[5] == "短码"
    assert LIST_KPI_COL == 14
    assert {10, 11, 12, 13, 14} == LIST_MONEY_COLS


def test_part_short_code_by_level() -> None:
    assert part_short_code(part_number="501029961AA", level=0) == "9961"
    assert part_short_code(part_number="501005123AA-1", level=1) == "5123AA-1"
    assert part_short_code(part_number="501005123AA", level=1) == "5123"
    assert part_short_code(part_number=None, level=0) == ""
