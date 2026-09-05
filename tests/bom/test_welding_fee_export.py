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


def test_part_short_code_by_level() -> None:
    assert part_short_code(part_number="501029961AA", level=0) == "9961"
    assert part_short_code(part_number="501005123AA-1", level=1) == "5123AA-1"
    assert part_short_code(part_number="501005123AA", level=1) == "5123"
    assert part_short_code(part_number=None, level=0) == ""
