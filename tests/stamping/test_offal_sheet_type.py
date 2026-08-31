"""料片式样拆利废。"""

from app.common.offal_nested import parse_offal_from_sheet_type


def test_parse_offal_side_panel_phrase() -> None:
    parsed = parse_offal_from_sheet_type("利用侧围废料")
    assert parsed.is_offal_nested is True
    assert parsed.offal_source == "侧围"
    assert parsed.sheet_type is None


def test_parse_offal_with_geometry() -> None:
    parsed = parse_offal_from_sheet_type("方料\n利用侧围废料")
    assert parsed.is_offal_nested is True
    assert parsed.offal_source == "侧围"
    assert parsed.sheet_type == "方料"


def test_parse_offal_bare_scrap_phrase() -> None:
    parsed = parse_offal_from_sheet_type("利用废料")
    assert parsed.is_offal_nested is True
    assert parsed.offal_source is None
    assert parsed.sheet_type is None


def test_parse_geometry_only() -> None:
    parsed = parse_offal_from_sheet_type("条料")
    assert parsed.is_offal_nested is False
    assert parsed.offal_source is None
    assert parsed.sheet_type == "条料"


def test_parse_empty_not_offal() -> None:
    parsed = parse_offal_from_sheet_type(None)
    assert parsed.is_offal_nested is False
    assert parsed.sheet_type is None


def test_parse_blank_length_not_offal() -> None:
    parsed = parse_offal_from_sheet_type("  ")
    assert parsed.is_offal_nested is False
