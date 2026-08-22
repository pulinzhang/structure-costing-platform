"""动因 TopN：区间起止差分与排序。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from app.repositories.llm.cost_analysis_repository import L0PartPeriodRow
from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow
from app.services.llm._money import money_str, month_key


def build_l0_drivers(
    rows: list[L0PartPeriodRow],
    *,
    top_n: int = 20,
) -> dict[str, Any]:
    by_part: dict[str, list[L0PartPeriodRow]] = defaultdict(list)
    for row in rows:
        by_part[row.part_number].append(row)

    drivers: list[dict[str, Any]] = []
    for part_number, items in by_part.items():
        ordered = sorted(items, key=lambda item: (item.year, item.month))
        first = ordered[0]
        last = ordered[-1]
        if month_key(first.year, first.month) == month_key(last.year, last.month):
            # 单月：按金额绝对值作「头部」
            drivers.append(
                {
                    "object_type": "l0",
                    "part_number": part_number,
                    "part_name": last.part_name,
                    "start_month": month_key(first.year, first.month),
                    "end_month": month_key(last.year, last.month),
                    "start_cost": money_str(first.grand_total),
                    "end_cost": money_str(last.grand_total),
                    "change": money_str(Decimal("0")),
                    "change_rate": None,
                    "end_value": money_str(last.grand_total),
                }
            )
            continue
        change = last.grand_total - first.grand_total
        rate = (
            (change / first.grand_total).quantize(Decimal("0.0001"))
            if first.grand_total != 0
            else None
        )
        drivers.append(
            {
                "object_type": "l0",
                "part_number": part_number,
                "part_name": last.part_name,
                "start_month": month_key(first.year, first.month),
                "end_month": month_key(last.year, last.month),
                "start_cost": money_str(first.grand_total),
                "end_cost": money_str(last.grand_total),
                "change": money_str(change),
                "change_rate": str(rate) if rate is not None else None,
                "end_value": money_str(last.grand_total),
            }
        )

    # 优先按涨幅，其次按期末金额
    def sort_key(item: dict[str, Any]) -> tuple[Decimal, Decimal]:
        rate = item.get("change_rate")
        rate_num = Decimal(rate) if rate is not None else Decimal("-999")
        end_val = Decimal(item.get("end_value") or "0")
        return (rate_num, end_val)

    ranked = sorted(drivers, key=sort_key, reverse=True)[:top_n]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {"kind": "drivers", "items": ranked, "top_n": top_n}


def build_stamping_drivers(
    rows: list[StampingPartPeriodRow],
    *,
    top_n: int = 20,
) -> dict[str, Any]:
    by_part: dict[str, list[StampingPartPeriodRow]] = defaultdict(list)
    for row in rows:
        by_part[row.part_number].append(row)

    drivers: list[dict[str, Any]] = []
    for part_number, items in by_part.items():
        ordered = sorted(items, key=lambda item: (item.year, item.month))
        first = ordered[0]
        last = ordered[-1]
        change = last.unit_cost - first.unit_cost
        rate = (
            (change / first.unit_cost).quantize(Decimal("0.0001"))
            if first.unit_cost != 0
            else None
        )
        drivers.append(
            {
                "object_type": "stamping_part",
                "part_number": part_number,
                "part_name": last.part_name,
                "start_cost": money_str(first.unit_cost),
                "end_cost": money_str(last.unit_cost),
                "change": money_str(change),
                "change_rate": str(rate) if rate is not None else None,
                "stamping_supplier": last.stamping_supplier,
            }
        )

    ranked = sorted(
        drivers,
        key=lambda item: Decimal(item["change_rate"] or "-999"),
        reverse=True,
    )[:top_n]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {"kind": "drivers", "items": ranked, "top_n": top_n}


def build_l0_mom_anomalies(
    rows: list[L0PartPeriodRow],
    *,
    top_n: int = 15,
    min_abs_change: Decimal = Decimal("1"),
    min_rate: Decimal = Decimal("0.05"),
) -> dict[str, Any]:
    """按月环比找费用跳变最大的零件（供「最大风险 / 异常核对」类问题）。"""
    by_part: dict[str, list[L0PartPeriodRow]] = defaultdict(list)
    for row in rows:
        by_part[row.part_number].append(row)

    spikes: list[dict[str, Any]] = []
    for part_number, items in by_part.items():
        ordered = sorted(items, key=lambda item: (item.year, item.month))
        for index in range(1, len(ordered)):
            prev_row = ordered[index - 1]
            curr_row = ordered[index]
            change = curr_row.grand_total - prev_row.grand_total
            rate: Decimal | None = None
            if prev_row.grand_total != 0:
                rate = (change / prev_row.grand_total).quantize(Decimal("0.0001"))
            if abs(change) < min_abs_change:
                if rate is None or abs(rate) < min_rate:
                    continue
            spikes.append(
                {
                    "anomaly_type": "mom_jump",
                    "part_number": part_number,
                    "part_name": curr_row.part_name,
                    "month": month_key(curr_row.year, curr_row.month),
                    "prev_month": month_key(prev_row.year, prev_row.month),
                    "prev_cost": money_str(prev_row.grand_total),
                    "curr_cost": money_str(curr_row.grand_total),
                    "change": money_str(change),
                    "change_rate": str(rate) if rate is not None else None,
                    "calc_status": curr_row.calc_status,
                }
            )

        for row in ordered:
            if row.calc_status == "ok":
                continue
            spikes.append(
                {
                    "anomaly_type": "calc_incomplete",
                    "part_number": part_number,
                    "part_name": row.part_name,
                    "month": month_key(row.year, row.month),
                    "prev_month": None,
                    "prev_cost": None,
                    "curr_cost": money_str(row.grand_total),
                    "change": None,
                    "change_rate": None,
                    "calc_status": row.calc_status,
                    "missing_leaf_count": row.missing_leaf_count,
                    "calc_message": (row.calc_message or "")[:120],
                }
            )

    def sort_key(item: dict[str, Any]) -> tuple[int, Decimal, Decimal]:
        if item.get("anomaly_type") == "calc_incomplete":
            return (2, Decimal("999999"), Decimal("0"))
        change_raw = item.get("change")
        rate_raw = item.get("change_rate")
        change_abs = abs(Decimal(change_raw)) if change_raw else Decimal("0")
        rate_abs = abs(Decimal(rate_raw)) if rate_raw else Decimal("0")
        return (1, change_abs, rate_abs)

    ranked = sorted(spikes, key=sort_key, reverse=True)[:top_n]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {"kind": "mom_anomalies", "items": ranked, "top_n": top_n}
