from decimal import Decimal
from pathlib import Path

import pytest

from app.common.swing_shear import (
    applied_swing_shear_fee_per_ton,
    contains_swing_shear,
    is_swing_shear_label,
    steel_kg_price_with_swing_shear,
)
from app.parsers.stamping.models.part import Part
from app.parsers.stamping.models.process import Process
from app.parsers.stamping.stamping_parser import parse_stamping_excel
from app.services.stamping.part.upload.swing_shear_resolver import collect_swing_shear_part_numbers


def test_is_swing_shear_label_matches_code_or_seq() -> None:
    assert is_swing_shear_label("摆剪", "OP05") is True
    assert is_swing_shear_label("落料", "OP05摆剪") is True
    assert is_swing_shear_label("拉伸", "OP10") is False
    assert is_swing_shear_label(None, None) is False


def test_contains_swing_shear_on_part_header_texts() -> None:
    assert contains_swing_shear("摆剪（28°）") is True
    assert contains_swing_shear("摆剪机") is True
    assert contains_swing_shear("铸造模", "双槽") is False


def test_applied_swing_shear_fee_snapshots_setting() -> None:
    assert applied_swing_shear_fee_per_ton(
        has_swing_shear=False, fee_per_ton=Decimal("150")
    ) == Decimal("0")
    assert applied_swing_shear_fee_per_ton(
        has_swing_shear=True, fee_per_ton=Decimal("150")
    ) == Decimal("150")
    assert steel_kg_price_with_swing_shear(Decimal("4269"), Decimal("150")) == Decimal("4.419")


_T2AA_PROCESS = (
    Path(__file__).resolve().parents[2]
    / "excel_sample"
    / "T2AA"
    / "T2AA项目冲压模具布点工艺清单（加凸焊信息)V0-01-2026-08-18（模版）(1).xlsx"
)


@pytest.mark.skipif(not _T2AA_PROCESS.is_file(), reason="T2AA 工艺确认表样本未放入 excel_sample")
def test_t2aa_c_pillar_parts_are_swing_shear() -> None:
    """摆剪写在零件首行工序内容/吨位，没有工序名称，仍应落主表标记。"""
    result = parse_stamping_excel(str(_T2AA_PROCESS))
    left = next(part for part in result.parts if part.part_number == "502018915AA")
    right = next(part for part in result.parts if part.part_number == "502018916AA")
    assert left.has_swing_shear is True
    assert right.has_swing_shear is True
    inner = next(part for part in result.parts if part.part_number == "501029963AA")
    assert inner.has_swing_shear is False


_HAIZHONG_T28 = (
    Path(__file__).resolve().parents[2]
    / "excel_sample"
    / "stamping"
    / "副本奇瑞T28车身件项目冲压工艺确认表-烟台海众.xlsx"
)


def test_merge_mate_inherits_previous_swing_shear() -> None:
    parts = [
        Part(part_number="502005519AA", process_method="合并"),
        Part(part_number="502005520AA", process_method="合并"),
    ]
    processes = [
        Process(part_number="502005519AA", process_seq="OP05", process_code="摆剪"),
        Process(part_number="502005519AA", process_seq="OP10", process_code="DR"),
        Process(part_number="502005520AA", process_seq="OP10", process_code="合并"),
        Process(part_number="502005520AA", process_seq="OP20", process_code=""),
    ]
    numbers = collect_swing_shear_part_numbers(parts, processes)
    assert "502005519AA" in numbers
    assert "502005520AA" in numbers


def test_unrelated_merge_left_does_not_inherit_swing_shear() -> None:
    parts = [
        Part(part_number="A", has_swing_shear=True),
        Part(part_number="B", process_method="合并"),
    ]
    processes = [
        Process(part_number="A", process_seq="OP10", process_code="摆剪"),
        Process(part_number="B", process_seq="OP10", process_code="DR"),
    ]
    numbers = collect_swing_shear_part_numbers(parts, processes)
    assert "A" in numbers
    assert "B" not in numbers


@pytest.mark.skipif(
    not _HAIZHONG_T28.is_file(), reason="海众 T28 工艺确认表样本未放入 excel_sample"
)
def test_haizhong_t28_merge_mate_inherits_swing_shear() -> None:
    result = parse_stamping_excel(str(_HAIZHONG_T28))
    numbers = collect_swing_shear_part_numbers(result.parts, result.processes)
    assert "502005519AA" in numbers
    assert "502005520AA" in numbers
