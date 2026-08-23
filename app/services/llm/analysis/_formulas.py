"""B.6.1 确定性公式（trend / drivers / comparison）。"""

from __future__ import annotations

import statistics
from decimal import Decimal
from typing import Any

from app.services.llm._money import money_str, rate_str

ANOMALY_MIN_POINTS_FOR_STAT = 6
ANOMALY_RATE_THRESHOLD = Decimal("0.15")


def compute_mom_rate(prev: Decimal, current: Decimal) -> Decimal | None:
    if prev == 0:
        return None
    return ((current - prev) / prev).quantize(Decimal("0.01"))


def compute_cumulative_rate(
    first: Decimal,
    last: Decimal,
    *,
    single_month: bool = False,
) -> Decimal | None:
    if single_month:
        return None
    if first == 0:
        return None
    return ((last - first) / first).quantize(Decimal("0.01"))


def detect_anomaly_months(
    points: list[dict[str, Any]],
    *,
    rate_threshold: Decimal = ANOMALY_RATE_THRESHOLD,
) -> tuple[list[str], str | None]:
    """数据点 < 6：仅 15% 阈值；≥ 6：均值+2σ 或 15%。"""
    valid_points: list[tuple[str, Decimal]] = []
    for point in points:
        raw = point.get("mom_rate")
        month = point.get("month")
        if raw is None or month is None:
            continue
        valid_points.append((str(month), Decimal(str(raw))))

    if not valid_points:
        return [], None

    abs_rates = [abs(rate) for _, rate in valid_points]
    use_stat_rule = len(valid_points) >= ANOMALY_MIN_POINTS_FOR_STAT
    stat_threshold = Decimal("0")
    if use_stat_rule:
        avg_abs = sum(abs_rates, start=Decimal("0")) / Decimal(len(abs_rates))
        if len(abs_rates) >= 2:
            stddev = Decimal(
                str(statistics.pstdev([float(value) for value in abs_rates]))
            )
        else:
            stddev = Decimal("0")
        stat_threshold = avg_abs + Decimal("2") * stddev

    anomaly_months: list[str] = []
    note_parts: list[str] = []
    for month, rate in valid_points:
        abs_rate = abs(rate)
        is_anomaly = abs_rate > rate_threshold
        if use_stat_rule and abs_rate > stat_threshold:
            is_anomaly = True
        if is_anomaly:
            anomaly_months.append(month)
            note_parts.append(f"{month} {rate_str(abs_rate)}")

    if not anomaly_months:
        return [], None

    note = f"异常环比：{'，'.join(note_parts)}，建议核查原因"
    return anomaly_months, note


def _parse_change_decimal(item: dict[str, Any]) -> Decimal:
    raw = item.get("change")
    if raw is None:
        return Decimal("0")
    return Decimal(str(raw))


def build_drivers_payload(
    drivers: list[dict[str, Any]],
    *,
    top_n: int,
) -> dict[str, Any]:
    """输出 top_items / up_contribution / down_drag（B.6.1）。"""
    ranked_top = sorted(
        drivers,
        key=lambda item: abs(_parse_change_decimal(item)),
        reverse=True,
    )[:top_n]

    up_items = [item for item in drivers if _parse_change_decimal(item) > 0]
    down_items = [item for item in drivers if _parse_change_decimal(item) < 0]

    up_ranked = sorted(
        up_items,
        key=lambda item: _parse_change_decimal(item),
        reverse=True,
    )[:top_n]
    positive_sum = sum(
        (_parse_change_decimal(item) for item in up_items),
        start=Decimal("0"),
    )
    up_contribution: list[dict[str, Any]] = []
    cumulative = Decimal("0")
    for index, item in enumerate(up_ranked, start=1):
        change = _parse_change_decimal(item)
        contribution = (
            (change / positive_sum).quantize(Decimal("0.01"))
            if positive_sum > 0
            else Decimal("0")
        )
        cumulative += contribution
        up_contribution.append(
            {
                **item,
                "rank": index,
                "contribution": rate_str(contribution),
                "contribution_pct": f"{contribution * 100:.2f}%",
            }
        )

    down_drag = sorted(
        down_items,
        key=lambda item: abs(_parse_change_decimal(item)),
        reverse=True,
    )[:top_n]
    for index, item in enumerate(down_drag, start=1):
        item["rank"] = index
        item["drag_label"] = "拖累项"

    concentration = "分散"
    if up_contribution and cumulative >= Decimal("0.60"):
        concentration = "集中"

    for index, item in enumerate(ranked_top, start=1):
        item["rank"] = index

    return {
        "kind": "drivers",
        "top_n": top_n,
        "top_items": ranked_top,
        "up_contribution": up_contribution,
        "down_drag": down_drag,
        "concentration": concentration,
        "top_cumulative_contribution": rate_str(cumulative),
    }


def compute_change_rate(first: Decimal, last: Decimal) -> Decimal | None:
    if first == 0:
        return None
    return ((last - first) / first).quantize(Decimal("0.01"))


def compute_spread(rate_a: Decimal | None, rate_b: Decimal | None) -> dict[str, Any]:
    if rate_a is None or rate_b is None:
        return {"spread": None, "status": "invalid"}
    spread = (rate_a - rate_b).quantize(Decimal("0.01"))
    return {"spread": rate_str(spread), "status": "valid"}


def build_period_diff(
    start_row: Any,
    end_row: Any,
) -> dict[str, Any]:
    """drilldown 区间差分：首末月 + 成本子项分解。"""
    components_spec = (
        ("processing", "加工", "stamping_amount"),
        ("purchased", "外购", "purchased_amount"),
        ("bundle", "一口价", "bundle_amount"),
        ("welding", "焊接", "welding_amount"),
    )

    start_total = Decimal(str(start_row.grand_total or 0))
    end_total = Decimal(str(end_row.grand_total or 0))
    delta = end_total - start_total
    delta_rate = compute_change_rate(start_total, end_total)

    component_rows: list[dict[str, Any]] = []
    abs_sum = Decimal("0")
    for code, label, attr in components_spec:
        start_value = Decimal(str(getattr(start_row, attr, 0) or 0))
        end_value = Decimal(str(getattr(end_row, attr, 0) or 0))
        component_delta = end_value - start_value
        abs_sum += abs(component_delta)
        component_rows.append(
            {
                "cost_component": code,
                "label": label,
                "start": money_str(start_value),
                "end": money_str(end_value),
                "delta": money_str(component_delta),
                "share": None,
            }
        )

    for item in component_rows:
        component_delta = Decimal(str(item["delta"]))
        share = (
            (abs(component_delta) / abs_sum).quantize(Decimal("0.01"))
            if abs_sum > 0
            else Decimal("0")
        )
        item["share"] = rate_str(share)

    return {
        "start_month": f"{start_row.year:04d}-{start_row.month:02d}",
        "end_month": f"{end_row.year:04d}-{end_row.month:02d}",
        "start_value": money_str(start_total),
        "end_value": money_str(end_total),
        "delta": money_str(delta),
        "delta_rate": rate_str(delta_rate) if delta_rate is not None else None,
        "components": component_rows,
    }


def format_missing_price_message(count: int) -> str:
    if count <= 0:
        return ""
    return (
        f"已排除 {count} 条缺价记录（单价为空或0），"
        "实际有效成本基于剩余记录计算"
    )
