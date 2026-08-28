"""模具分摊比例：共模 0.50，级进模不加 0.80。"""

from decimal import Decimal

from app.parsers.stamping_die.parser import parse_unit_interval
from app.services.stamping.die.alloc_ratio_resolver import resolve_alloc_ratio


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
