"""冲压零件核价导出须选定项目。"""

from decimal import Decimal

import pytest

from app.exceptions.base import BusinessException
from app.services.costing.stamping_part_cost.export.process_sheet import PROCESS_SHEET_HEADERS
from app.services.costing.stamping_part_cost.export.tailor_weld_display import (
    build_blank_row_m_formula,
    build_tailor_group_n_formula,
    build_tailor_group_o_formula,
)
from app.services.costing.stamping_part_cost.stamping_part_cost_export_service import (
    EXPORT_VEHICLE_REQUIRED_MESSAGE,
    require_export_vehicle_model,
)


def test_require_export_vehicle_model_accepts_name() -> None:
    assert require_export_vehicle_model(" T2AA ") == "T2AA"


@pytest.mark.parametrize("value", [None, "", "   "])
def test_require_export_vehicle_model_rejects_blank(value: str | None) -> None:
    with pytest.raises(BusinessException, match=EXPORT_VEHICLE_REQUIRED_MESSAGE):
        require_export_vehicle_model(value)


def test_process_sheet_short_code_after_part_number() -> None:
    titles = [title for _letter, title in PROCESS_SHEET_HEADERS]
    assert titles[2] == "零件号"
    assert titles[3] == "短码"
    assert titles[4] == "零件名称"
    assert PROCESS_SHEET_HEADERS[3][0] == "D"
    assert PROCESS_SHEET_HEADERS[-1] == ("AQ", "摆剪加价(元/吨)")
    assert PROCESS_SHEET_HEADERS[-2] == ("AP", "是否摆剪")
    letters = [letter for letter, _title in PROCESS_SHEET_HEADERS]
    assert letters[0] == "A"
    assert letters[-1] == "AQ"
    assert len(letters) == len(set(letters))


def test_tailor_formulas_use_columns_after_short_code() -> None:
    formula = build_blank_row_m_formula(5, Decimal("7.85"))
    assert "K5*L5*H5" in formula
    assert formula.endswith("/M5")
    assert build_tailor_group_n_formula(5, 7) == "=I5/SUM(N5:N7)"
    assert build_tailor_group_o_formula(5, 7) == "=SUM(N5:N7)-I5"
