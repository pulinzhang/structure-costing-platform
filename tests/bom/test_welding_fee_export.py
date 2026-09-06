"""焊接费导出：零件短代码。"""

from app.services.bom.welding_fee.export_service import (
    COL,
    COL_COUNT,
    HEADERS,
    MAIN_COLS,
    part_short_code,
)


def test_short_code_column_after_part_number() -> None:
    assert HEADERS[6] == "零件号"
    assert HEADERS[7] == "短代码"
    assert MAIN_COLS == 19
    assert COL_COUNT == 26
    assert COL["短代码"] == 8
    assert COL["行费"] == 25


def test_compact_layout_drops_scope_columns() -> None:
    from app.services.bom.welding_fee.export_service import WeldingSheetLayout

    layout = WeldingSheetLayout(omit_scope=True)
    assert "年度" not in layout.headers
    assert "基地" not in layout.headers
    assert layout.headers[0] == "序号"
    assert layout.headers[1] == "层级"
    assert layout.col["零件号"] == 3
    assert layout.main_cols == 15
    assert layout.col_count == 22


def test_part_short_code_by_level() -> None:
    assert part_short_code(part_number="501029961AA", level=0) == "9961"
    assert part_short_code(part_number="501005123AA-1", level=1) == "5123AA-1"
    assert part_short_code(part_number="501005123AA", level=1) == "5123"
    assert part_short_code(part_number=None, level=0) == ""
