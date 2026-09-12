"""B.6.1 核心算法单测。"""

from __future__ import annotations

from decimal import Decimal

from app.services.llm.analysis.shared.formulas import (
    ANOMALY_MIN_POINTS_FOR_STAT,
    build_drivers_payload,
    build_period_diff,
    compute_change_rate,
    compute_cumulative_rate,
    compute_mom_rate,
    compute_spread,
    detect_anomaly_months,
    format_missing_price_message,
)


def test_mom_rate_zero_denominator_returns_none() -> None:
    assert compute_mom_rate(Decimal("0"), Decimal("100")) is None


def test_cumulative_rate_matches_design() -> None:
    rate = compute_cumulative_rate(Decimal("1000"), Decimal("1100"))
    assert rate == Decimal("0.10")


def test_cumulative_rate_single_month_is_null() -> None:
    assert compute_cumulative_rate(Decimal("1000"), Decimal("1100"), single_month=True) is None


def test_anomaly_months_threshold_15_percent_when_few_points() -> None:
    points = [
        {"month": "2026-01", "mom_rate": "0.05"},
        {"month": "2026-02", "mom_rate": "0.16"},
    ]
    months, note = detect_anomaly_months(points)
    assert len(points) < ANOMALY_MIN_POINTS_FOR_STAT
    assert months == ["2026-02"]
    assert note is not None
    assert "建议核查原因" in note


def test_anomaly_months_uses_stat_rule_when_enough_points() -> None:
    points = [{"month": f"2026-{month:02d}", "mom_rate": "0.02"} for month in range(1, 7)]
    points[-1] = {"month": "2026-06", "mom_rate": "0.20"}
    months, note = detect_anomaly_months(points)
    assert "2026-06" in months
    assert note is not None


def test_drivers_split_up_and_down() -> None:
    drivers = [
        {"part_number": "A", "change": "10.00"},
        {"part_number": "B", "change": "-50.00"},
        {"part_number": "C", "change": "5.00"},
    ]
    payload = build_drivers_payload(drivers, top_n=2)
    assert payload["top_items"][0]["part_number"] == "B"
    assert payload["up_contribution"][0]["part_number"] == "A"
    assert payload["up_contribution"][0]["contribution"] == "0.67"
    assert payload["down_drag"][0]["part_number"] == "B"
    assert payload["down_drag"][0]["drag_label"] == "拖累项"


def test_comparison_spread_invalid_when_denominator_zero() -> None:
    assert compute_spread(None, Decimal("0.10"))["status"] == "invalid"
    assert compute_spread(Decimal("0.10"), Decimal("0.05"))["spread"] == "0.05"


def test_change_rate_zero_denominator() -> None:
    assert compute_change_rate(Decimal("0"), Decimal("10")) is None


def test_format_missing_price_message() -> None:
    assert "已排除 3 条缺价记录" in format_missing_price_message(3)
    assert format_missing_price_message(0) == ""


def test_build_period_diff_components() -> None:
    from types import SimpleNamespace

    start = SimpleNamespace(
        year=2026,
        month=1,
        grand_total=Decimal("100"),
        stamping_amount=Decimal("40"),
        purchased_amount=Decimal("30"),
        bundle_amount=Decimal("10"),
        welding_amount=Decimal("20"),
    )
    end = SimpleNamespace(
        year=2026,
        month=3,
        grand_total=Decimal("150"),
        stamping_amount=Decimal("60"),
        purchased_amount=Decimal("40"),
        bundle_amount=Decimal("10"),
        welding_amount=Decimal("40"),
    )
    diff = build_period_diff(start, end)
    assert diff["delta"] == "50.00"
    assert diff["delta_rate"] == "0.50"
    assert len(diff["components"]) == 4
