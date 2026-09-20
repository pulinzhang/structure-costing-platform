"""模具分摊比例：共模 0.50，级进模不加 0.80。"""

from decimal import Decimal

from app.parsers.stamping.die.parser import ParsedDiePart, ParsedDieProcess, parse_unit_interval
from app.services.stamping.die.upload.alloc_preserver import resolve_part_ratios
from app.services.stamping.die.upload.alloc_ratio_resolver import resolve_alloc_ratio


def test_shared_die_is_0_50() -> None:
    assert resolve_alloc_ratio("双槽", "手工线") == Decimal("0.50")
    assert resolve_alloc_ratio("左右合并", None) == Decimal("0.50")
    assert resolve_alloc_ratio("一出二", "自动化") == Decimal("0.50")


def test_progressive_die_alone_is_1_00() -> None:
    assert resolve_alloc_ratio("单干", "级进模") == Decimal("1.00")


def test_progressive_plus_shared_is_0_50_not_0_40() -> None:
    assert resolve_alloc_ratio("合并", "级进模") == Decimal("0.50")
    assert resolve_alloc_ratio("双槽", "级进模") == Decimal("0.50")


def test_material_utilization_percent_to_unit_interval() -> None:
    assert parse_unit_interval(65) == Decimal("0.6500")
    assert parse_unit_interval("65%") == Decimal("0.6500")
    assert parse_unit_interval(0.65) == Decimal("0.6500")
    assert parse_unit_interval("0.65") == Decimal("0.6500")
    assert parse_unit_interval("#VALUE!") is None


def test_scrap_byproduct_alloc_is_zero_and_overrides_preserved() -> None:
    process = ParsedDieProcess(
        process_seq="OP10",
        process_code="合并",
        die_sets=1,
        die_number=None,
        die_length=None,
        die_width=None,
        die_height=None,
        hollow_factor=None,
        estimated_weight_t=None,
        tonnage=None,
        excel_row=10,
    )
    part = ParsedDiePart(
        seq_no=26,
        part_number="502018924AA",
        part_name="左D柱下隔板",
        material=None,
        thickness=None,
        part_weight=Decimal("0.079"),
        sheet_length=None,
        sheet_width=None,
        sheet_shape=None,
        parts_per_sheet=None,
        material_consumption=None,
        material_utilization=None,
        estimated_weight_subtotal_t=None,
        die_type=None,
        die_method="双槽",
        production_mode=None,
        needs_end_effector=None,
        part_grade=None,
        remark=None,
        excel_sheet_name="布点",
        excel_row=179,
        excel_part_col=2,
        is_scrap_byproduct=True,
        processes=[process],
    )
    ratios = resolve_part_ratios(part, {"502018924AA": {"OP10": Decimal("0.50")}})
    assert ratios == [Decimal("0.00")]
