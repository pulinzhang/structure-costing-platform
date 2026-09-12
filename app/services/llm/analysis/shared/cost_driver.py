"""动因 TopN：上涨贡献 / 下跌拖累（B.6.1）。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from app.repositories.llm.cost_analysis_repository import L0PartPeriodRow
from app.repositories.llm.l0_welding_fee_analysis_repository import L0WeldingFeeRow
from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow
from app.services.llm._money import money_str, month_key, rate_str
from app.services.llm.analysis.shared.constants import (
    ASSEMBLY_UNIT_PRICE_MOM_THRESHOLD,
    DEFAULT_DRIVER_TOP_N,
)
from app.services.llm.analysis.shared.formulas import (
    assembly_unit_price,
    build_drivers_payload,
    compute_change_rate,
)


def _is_priced_unit(unit_price: Decimal | None) -> bool:
    return unit_price is not None and unit_price > 0


def build_l0_drivers(
    rows: list[L0PartPeriodRow],
    *,
    top_n: int = DEFAULT_DRIVER_TOP_N,
) -> dict[str, Any]:
    priced_rows = [row for row in rows if _is_priced_unit(assembly_unit_price(row))]
    by_part: dict[str, list[L0PartPeriodRow]] = defaultdict(list)
    for row in priced_rows:
        by_part[row.part_number].append(row)

    drivers: list[dict[str, Any]] = []
    for part_number, items in by_part.items():
        ordered = sorted(items, key=lambda item: (item.year, item.month))
        first = ordered[0]
        last = ordered[-1]
        first_price = assembly_unit_price(first)
        last_price = assembly_unit_price(last)
        change = last_price - first_price
        rate = compute_change_rate(first_price, last_price)
        drivers.append(
            {
                "object_type": "l0",
                "part_number": part_number,
                "part_name": last.part_name,
                "start_month": month_key(first.year, first.month),
                "end_month": month_key(last.year, last.month),
                "start_cost": money_str(first_price),
                "end_cost": money_str(last_price),
                "change": money_str(change),
                "change_rate": rate_str(rate) if rate is not None else None,
                "end_value": money_str(last_price),
            }
        )

    return build_drivers_payload(drivers, top_n=top_n)


def build_stamping_drivers(
    rows: list[StampingPartPeriodRow],
    *,
    top_n: int = DEFAULT_DRIVER_TOP_N,
) -> dict[str, Any]:
    priced_rows = [row for row in rows if row.unit_cost is not None and row.unit_cost > 0]
    by_part: dict[str, list[StampingPartPeriodRow]] = defaultdict(list)
    for row in priced_rows:
        by_part[row.part_number].append(row)

    drivers: list[dict[str, Any]] = []
    for part_number, items in by_part.items():
        ordered = sorted(items, key=lambda item: (item.year, item.month))
        first = ordered[0]
        last = ordered[-1]
        change = last.unit_cost - first.unit_cost
        rate = compute_change_rate(first.unit_cost, last.unit_cost)
        drivers.append(
            {
                "object_type": "stamping_part",
                "part_number": part_number,
                "part_name": last.part_name,
                "start_cost": money_str(first.unit_cost),
                "end_cost": money_str(last.unit_cost),
                "change": money_str(change),
                "change_rate": rate_str(rate) if rate is not None else None,
                "stamping_supplier": last.stamping_supplier,
            }
        )

    return build_drivers_payload(drivers, top_n=top_n)


def build_l0_mom_anomalies(
    rows: list[L0PartPeriodRow],
    *,
    top_n: int = 15,
    min_rate: Decimal | None = None,
    focus_month: str | None = None,
) -> dict[str, Any]:
    """按月环比找单价跳变：相对上月绝对值 ≥ 10%（或从上月 0 变成有价）。"""
    rate_threshold = (
        min_rate if min_rate is not None else Decimal(ASSEMBLY_UNIT_PRICE_MOM_THRESHOLD)
    )
    by_part: dict[str, list[L0PartPeriodRow]] = defaultdict(list)
    for row in rows:
        by_part[row.part_number].append(row)

    spikes: list[dict[str, Any]] = []
    for part_number, items in by_part.items():
        ordered = sorted(items, key=lambda item: (item.year, item.month))
        for index in range(1, len(ordered)):
            prev_row = ordered[index - 1]
            curr_row = ordered[index]
            prev_price = assembly_unit_price(prev_row)
            curr_price = assembly_unit_price(curr_row)
            rate = compute_change_rate(prev_price, curr_price) if prev_price > 0 else None
            is_mom_jump = rate is not None and abs(rate) >= rate_threshold
            is_from_zero = prev_price == 0 and curr_price > 0
            if not is_mom_jump and not is_from_zero:
                continue
            change = curr_price - prev_price
            spikes.append(
                {
                    "anomaly_type": "mom_jump",
                    "part_number": part_number,
                    "part_name": curr_row.part_name,
                    "month": month_key(curr_row.year, curr_row.month),
                    "prev_month": month_key(prev_row.year, prev_row.month),
                    "prev_cost": money_str(prev_price),
                    "curr_cost": money_str(curr_price),
                    "change": money_str(change),
                    "change_rate": rate_str(rate) if rate is not None else None,
                    "calc_status": curr_row.calc_status,
                    "threshold": str(rate_threshold),
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
                    "curr_cost": money_str(assembly_unit_price(row)),
                    "change": None,
                    "change_rate": None,
                    "calc_status": row.calc_status,
                    "missing_leaf_count": row.missing_leaf_count,
                    "calc_message": (row.calc_message or "")[:120],
                }
            )

    if focus_month:
        spikes = [item for item in spikes if item.get("month") == focus_month]
    return _rank_mom_spikes(spikes, top_n=top_n)


def _rank_mom_spikes(spikes: list[dict[str, Any]], *, top_n: int) -> dict[str, Any]:
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


def _mom_rate_threshold(min_rate: Decimal | None) -> Decimal:
    if min_rate is not None:
        return min_rate
    return Decimal(ASSEMBLY_UNIT_PRICE_MOM_THRESHOLD)


def _is_mom_or_from_zero(prev_price: Decimal, curr_price: Decimal, rate_threshold: Decimal) -> bool:
    rate = compute_change_rate(prev_price, curr_price) if prev_price > 0 else None
    is_mom_jump = rate is not None and abs(rate) >= rate_threshold
    is_from_zero = prev_price == 0 and curr_price > 0
    return is_mom_jump or is_from_zero


def build_stamping_mom_anomalies(
    rows: list[StampingPartPeriodRow],
    *,
    top_n: int = 15,
    min_rate: Decimal | None = None,
    focus_month: str | None = None,
) -> dict[str, Any]:
    """冲压零件单价环比：相对上月绝对值 ≥ 10%。"""
    rate_threshold = _mom_rate_threshold(min_rate)
    by_part: dict[str, list[StampingPartPeriodRow]] = defaultdict(list)
    for row in rows:
        by_part[f"{row.part_number}|{row.stamping_supplier}"].append(row)

    spikes: list[dict[str, Any]] = []
    for _key, items in by_part.items():
        ordered = sorted(items, key=lambda item: (item.year, item.month))
        for index in range(1, len(ordered)):
            prev_row = ordered[index - 1]
            curr_row = ordered[index]
            prev_price = prev_row.unit_cost
            curr_price = curr_row.unit_cost
            if not _is_mom_or_from_zero(prev_price, curr_price, rate_threshold):
                continue
            rate = compute_change_rate(prev_price, curr_price) if prev_price > 0 else None
            spikes.append(
                {
                    "anomaly_type": "mom_jump",
                    "part_number": curr_row.part_number,
                    "part_name": curr_row.part_name,
                    "month": month_key(curr_row.year, curr_row.month),
                    "prev_month": month_key(prev_row.year, prev_row.month),
                    "prev_cost": money_str(prev_price),
                    "curr_cost": money_str(curr_price),
                    "change": money_str(curr_price - prev_price),
                    "change_rate": rate_str(rate) if rate is not None else None,
                    "calc_status": curr_row.calc_status,
                    "stamping_supplier": curr_row.stamping_supplier,
                    "threshold": str(rate_threshold),
                }
            )
        for row in ordered:
            if row.calc_status == "success":
                continue
            spikes.append(
                {
                    "anomaly_type": "calc_incomplete",
                    "part_number": row.part_number,
                    "part_name": row.part_name,
                    "month": month_key(row.year, row.month),
                    "prev_month": None,
                    "prev_cost": None,
                    "curr_cost": money_str(row.unit_cost),
                    "change": None,
                    "change_rate": None,
                    "calc_status": row.calc_status,
                    "stamping_supplier": row.stamping_supplier,
                }
            )

    if focus_month:
        spikes = [item for item in spikes if item.get("month") == focus_month]
    return _rank_mom_spikes(spikes, top_n=top_n)


def _welding_fee_amount(row: L0WeldingFeeRow) -> Decimal:
    if row.final_l0_welding_fee is not None:
        return row.final_l0_welding_fee
    return row.total_l0_welding_fee


def _welding_fee_key(row: L0WeldingFeeRow) -> str:
    return f"{row.location}|{row.vehicle_model}|{row.bom_version}|{row.part_number}"


def build_welding_fee_mom_anomalies(
    rows: list[L0WeldingFeeRow],
    *,
    top_n: int = 15,
    min_rate: Decimal | None = None,
    focus_year: int | None = None,
) -> dict[str, Any]:
    """焊接费按年核算：相对上年绝对值 ≥ 10%。问某月时用该年结果对上年。"""
    rate_threshold = _mom_rate_threshold(min_rate)
    by_part: dict[str, list[L0WeldingFeeRow]] = defaultdict(list)
    for row in rows:
        by_part[_welding_fee_key(row)].append(row)

    spikes: list[dict[str, Any]] = []
    for _key, items in by_part.items():
        ordered = sorted(items, key=lambda item: item.year)
        for index in range(1, len(ordered)):
            prev_row = ordered[index - 1]
            curr_row = ordered[index]
            if curr_row.year != prev_row.year + 1:
                continue
            prev_price = _welding_fee_amount(prev_row)
            curr_price = _welding_fee_amount(curr_row)
            if not _is_mom_or_from_zero(prev_price, curr_price, rate_threshold):
                continue
            rate = compute_change_rate(prev_price, curr_price) if prev_price > 0 else None
            spikes.append(
                {
                    "anomaly_type": "mom_jump",
                    "part_number": curr_row.part_number,
                    "part_name": curr_row.part_name,
                    "month": f"{curr_row.year:04d}",
                    "prev_month": f"{prev_row.year:04d}",
                    "prev_cost": money_str(prev_price),
                    "curr_cost": money_str(curr_price),
                    "change": money_str(curr_price - prev_price),
                    "change_rate": rate_str(rate) if rate is not None else None,
                    "calc_status": curr_row.calc_status,
                    "vehicle_model": curr_row.vehicle_model,
                    "threshold": str(rate_threshold),
                    "period_grain": "year",
                }
            )
        for row in ordered:
            if row.calc_status == "ok":
                continue
            spikes.append(
                {
                    "anomaly_type": "calc_incomplete",
                    "part_number": row.part_number,
                    "part_name": row.part_name,
                    "month": f"{row.year:04d}",
                    "prev_month": None,
                    "prev_cost": None,
                    "curr_cost": money_str(_welding_fee_amount(row)),
                    "change": None,
                    "change_rate": None,
                    "calc_status": row.calc_status,
                    "vehicle_model": row.vehicle_model,
                    "period_grain": "year",
                }
            )

    if focus_year is not None:
        focus = f"{focus_year:04d}"
        spikes = [item for item in spikes if item.get("month") == focus]
    return _rank_mom_spikes(spikes, top_n=top_n)
