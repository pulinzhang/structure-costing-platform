"""冷轧、酸洗非 1250，镀锌非 1250/1500，只告警不拒绝。"""

from decimal import Decimal

from app.services.yishiyiyi.base_price.gate import (
    AwardLine,
    reference_width_note,
    unexpected_reference_width_warnings,
)


def _line(
    *,
    category_name: str,
    width: str | None,
    grade: str = "DC01",
    location: str = "芜湖",
    excel_row: int | None = 8,
) -> AwardLine:
    return AwardLine(
        location=location,
        grade=grade,
        steel_mill="邯钢",
        thick=Decimal("1"),
        width=None if width is None else Decimal(width),
        category_name=category_name,
        excel_row=excel_row,
    )


def test_common_widths_are_silent() -> None:
    assert (
        unexpected_reference_width_warnings(
            [
                _line(category_name="冷轧", width="1250"),
                _line(category_name="酸洗", width="1250.00", grade="SPHC"),
                _line(category_name="镀锌", width="1250", grade="DC51D+Z"),
                _line(category_name="镀锌", width="1500", grade="DC56D+Z"),
            ]
        )
        == []
    )


def test_cold_rolled_and_pickled_other_widths_warn_without_raising() -> None:
    warnings = unexpected_reference_width_warnings(
        [
            _line(category_name="冷轧", width="1500"),
            _line(category_name="酸洗", width="1500", grade="SPHC", excel_row=9),
        ]
    )
    assert len(warnings) == 1
    assert "冷轧参考宽度是 1500 mm，常见是 1250 mm" in warnings[0]
    assert "酸洗参考宽度是 1500 mm，常见是 1250 mm" in warnings[0]
    assert "已经保存" in warnings[0]


def test_galvanized_other_width_warns() -> None:
    warnings = unexpected_reference_width_warnings(
        [_line(category_name="镀锌", width="1600", grade="DC56D+Z")]
    )
    assert len(warnings) == 1
    assert "镀锌参考宽度是 1600 mm，常见是 1250、1500 mm" in warnings[0]


def test_note_is_built_from_the_allowlist() -> None:
    note = reference_width_note()
    assert "冷轧、酸洗常见 1250 mm" in note
    assert "镀锌常见 1250、1500 mm" in note


def test_missing_width_is_not_this_warning() -> None:
    assert unexpected_reference_width_warnings([_line(category_name="冷轧", width=None)]) == []
