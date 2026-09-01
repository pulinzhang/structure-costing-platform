"""焊接信息原文拆解：材料清单常见写法。"""

from decimal import Decimal

from app.common.bom.welding_standard_process import WeldingStandardProcessName
from app.parsers.bom.welding_process_breakdown_parser import parse_welding_info_text


def test_double_colon_projection_weld() -> None:
    result = parse_welding_info_text("凸焊:：2")
    assert result.parse_status == "ok"
    assert len(result.items) == 1
    item = result.items[0]
    assert item.process_token == "凸焊"
    assert item.process_qty == Decimal("2")
    assert item.standard_process_name == WeldingStandardProcessName.STUD_PROJECTION_WELD.value
    assert item.map_status == "ready"


def test_e_coat_black_paint_area() -> None:
    result = parse_welding_info_text("电泳黑漆：0.098m2")
    assert result.parse_status == "ok"
    assert len(result.items) == 1
    item = result.items[0]
    assert item.process_token == "电泳面积"
    assert item.process_qty == Decimal("0.098")
    assert item.process_qty_unit == "m2"
    assert item.standard_process_name == WeldingStandardProcessName.E_COAT_LE_244H.value
    assert item.map_status == "ready"


def test_existing_e_coat_area_and_spot_glue_still_parse() -> None:
    mixed = parse_welding_info_text("黒漆件 电泳面积：0.017m2")
    assert mixed.parse_status == "ok"
    assert mixed.items[0].process_qty == Decimal("0.017")

    rivet = parse_welding_info_text("铆接：1 电泳+ 喷粉（黑色） 面积：0.014m2")
    assert rivet.parse_status == "ok"
    tokens = {item.process_token for item in rivet.items}
    assert "铆接" in tokens
    assert "面积" in tokens
