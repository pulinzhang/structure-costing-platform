"""新增工序默认费用比例：级进模 ×0.80，一出二/双槽/合并再 ÷2。"""

from decimal import Decimal

from app.services.stamping.upload.cost_ratio_resolver import resolve_cost_ratio


def test_progressive_die_only_is_0_80() -> None:
    assert resolve_cost_ratio("级进模", None) == Decimal("0.80")
    assert resolve_cost_ratio("级进模", "单件") == Decimal("0.80")


def test_one_out_of_two_only_is_0_50() -> None:
    assert resolve_cost_ratio(None, "一出二") == Decimal("0.50")


def test_progressive_die_and_one_out_of_two_is_0_40() -> None:
    assert resolve_cost_ratio("级进模", "一出二") == Decimal("0.40")


def test_shared_die_keywords_still_halve() -> None:
    assert resolve_cost_ratio(None, "双槽") == Decimal("0.50")
    assert resolve_cost_ratio(None, "左右合并") == Decimal("0.50")
    assert resolve_cost_ratio("级进模", "双槽") == Decimal("0.40")
