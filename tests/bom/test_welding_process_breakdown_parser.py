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


def test_co2_weld_seam_without_parentheses() -> None:
    """T2AA 材料清单：焊缝：3条 68mm（条数与长度之间无括号）。"""
    result = parse_welding_info_text("焊缝：3条 68mm")
    assert result.parse_status == "ok"
    assert len(result.items) == 1
    item = result.items[0]
    assert item.process_token == "焊缝"
    assert item.process_qty == Decimal("3")
    assert item.process_qty_unit == "条"
    assert item.process_qty_secondary == Decimal("68")
    assert item.process_qty_secondary_unit == "mm"
    assert item.standard_process_name == WeldingStandardProcessName.CO2_WELD_SEAM.value
    assert item.map_status == "ready"

    with_parens = parse_welding_info_text("焊缝：3条（81mm）")
    assert with_parens.parse_status == "ok"
    assert with_parens.items[0].process_qty_secondary == Decimal("81")


def test_ground_stud_and_seam_length_sum() -> None:
    """T2AA：搭铁；焊缝长度写成（218+30）mm。"""
    rear = parse_welding_info_text("焊点：91个 凸焊：5个 植焊：5个 搭铁：3个")
    assert rear.parse_status == "ok"
    assert [item.process_token for item in rear.items] == ["焊点", "凸焊", "植焊", "搭铁"]
    ground = rear.items[3]
    assert ground.process_qty == Decimal("3")
    assert ground.standard_process_name == WeldingStandardProcessName.STUD_PROJECTION_WELD.value
    assert ground.map_status == "ready"

    side = parse_welding_info_text("焊缝：18条 （218+30）mm 凸焊：3个")
    assert side.parse_status == "ok"
    assert [item.process_token for item in side.items] == ["焊缝", "凸焊"]
    seam = side.items[0]
    assert seam.process_qty == Decimal("18")
    assert seam.process_qty_secondary == Decimal("248")
    assert seam.process_qty_secondary_unit == "mm"
    assert seam.standard_process_name == WeldingStandardProcessName.CO2_WELD_SEAM.value
    assert seam.map_status == "ready"
    assert side.items[1].process_qty == Decimal("3")


def test_existing_e_coat_area_and_spot_glue_still_parse() -> None:
    mixed = parse_welding_info_text("黒漆件 电泳面积：0.017m2")
    assert mixed.parse_status == "ok"
    assert mixed.items[0].process_qty == Decimal("0.017")

    rivet = parse_welding_info_text("铆接：1 电泳+ 喷粉（黑色） 面积：0.014m2")
    assert rivet.parse_status == "ok"
    tokens = {item.process_token for item in rivet.items}
    assert "铆接" in tokens
    assert "面积" in tokens
