from decimal import Decimal
from pathlib import Path

import pytest

from app.common.swing_shear import (
    applied_swing_shear_fee_per_ton,
    contains_swing_shear,
    is_swing_shear_label,
    steel_kg_price_with_swing_shear,
)
from app.parsers.stamping.stamping_parser import parse_stamping_excel


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
