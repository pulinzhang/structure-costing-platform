"""summary 分析：盘子 KPI。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from app.repositories.llm.cost_analysis import L0MonthlyTotalRow, L0PartPeriodRow
from app.repositories.llm.stamping_cost_analysis_repository import StampingPartPeriodRow
from app.repositories.llm.steel_price_analysis_repository import SteelMonthlyAvgRow
from app.services.llm._money import money_str, month_key


def _distinct_l0_status_counts(
    part_rows: list[L0PartPeriodRow],
) -> tuple[int, int, int]:
    """按零件号去重；任一月非 ok 则计为 partial。"""
    status_by_part: dict[str, str] = {}
    for row in part_rows:
        current = status_by_part.get(row.part_number)
        if current is None or row.calc_status != "ok":
            status_by_part[row.part_number] = row.calc_status
    total = len(status_by_part)
    partial_count = sum(1 for status in status_by_part.values() if status != "ok")
    ok_count = total - partial_count
    return total, ok_count, partial_count


def build_summary(
    rows: list[L0MonthlyTotalRow],
    *,
    part_rows: list[L0PartPeriodRow] | None = None,
) -> dict[str, Any]:
    if not rows:
        return {
            "l0_count": 0,
            "ok_count": 0,
            "partial_count": 0,
            "grand_total_sum": "0.0000",
            "total_amount_sum": "0.0000",
            "indirect_amount_sum": "0.0000",
            "breakdown": {},
            "months": [],
        }

    # 金额类指标：多月区间求和；件数类指标：按零件号去重，禁止「27×N 月=54/324」
    if part_rows:
        l0_count, ok_count, partial_count = _distinct_l0_status_counts(part_rows)
    elif len(rows) == 1:
        l0_count = rows[0].l0_count
        ok_count = rows[0].ok_count
        partial_count = rows[0].partial_count
    else:
        l0_count = max(row.l0_count for row in rows)
        ok_count = max(row.ok_count for row in rows)
        partial_count = max(row.partial_count for row in rows)
    grand = sum((row.grand_total_sum for row in rows), start=rows[0].grand_total_sum * 0)
    total = sum((row.total_amount_sum for row in rows), start=rows[0].total_amount_sum * 0)
    indirect = sum((row.indirect_amount_sum for row in rows), start=rows[0].indirect_amount_sum * 0)
    stamping = sum((row.stamping_amount_sum for row in rows), start=rows[0].stamping_amount_sum * 0)
    purchased = sum(
        (row.purchased_amount_sum for row in rows),
        start=rows[0].purchased_amount_sum * 0,
    )
    bundle = sum((row.bundle_amount_sum for row in rows), start=rows[0].bundle_amount_sum * 0)
    welding = sum((row.welding_amount_sum for row in rows), start=rows[0].welding_amount_sum * 0)
    welding_other = sum(
        (row.welding_other_amount_sum for row in rows),
        start=rows[0].welding_other_amount_sum * 0,
    )

    return {
        "l0_count": l0_count,
        "ok_count": ok_count,
        "partial_count": partial_count,
        "month_count": len(rows),
        "grand_total_sum": money_str(grand),
        "total_amount_sum": money_str(total),
        "indirect_amount_sum": money_str(indirect),
        "breakdown": {
            "stamping_amount_sum": money_str(stamping),
            "purchased_amount_sum": money_str(purchased),
            "bundle_amount_sum": money_str(bundle),
            "welding_amount_sum": money_str(welding),
            "welding_other_amount_sum": money_str(welding_other),
        },
        "months": [
            {
                "month": month_key(row.year, row.month),
                "location": row.location,
                "grand_total_sum": money_str(row.grand_total_sum),
                "l0_count": row.l0_count,
            }
            for row in rows
        ],
    }


def build_stamping_summary(rows: list[StampingPartPeriodRow]) -> dict[str, Any]:
    """冲压零件价格一览口径的 summary（对齐 #/stamping-part-cost）。"""
    if not rows:
        return {
            "subject": "stamping_part",
            "part_count": 0,
            "success_count": 0,
            "failed_count": 0,
            "unit_cost_sum": "0.0000",
            "avg_unit_cost": "0.0000",
            "material_net_sum": "0.0000",
            "process_fee_sum": "0.0000",
            "months": [],
        }

    success_count = sum(1 for row in rows if row.calc_status == "success")
    failed_count = len(rows) - success_count
    unit_sum = sum((row.unit_cost for row in rows), start=Decimal("0"))
    material_sum = sum(
        (row.material_net_per_part or Decimal("0") for row in rows),
        start=Decimal("0"),
    )
    process_sum = sum(
        (row.process_fee_amount or Decimal("0") for row in rows),
        start=Decimal("0"),
    )
    avg = (unit_sum / Decimal(len(rows))).quantize(Decimal("0.0001")) if rows else Decimal("0")

    by_month: dict[str, list[StampingPartPeriodRow]] = defaultdict(list)
    for row in rows:
        by_month[month_key(row.year, row.month)].append(row)

    months = []
    for month, items in sorted(by_month.items()):
        month_unit = sum((item.unit_cost for item in items), start=Decimal("0"))
        months.append(
            {
                "month": month,
                "part_count": len(items),
                "unit_cost_sum": money_str(month_unit),
                "success_count": sum(1 for item in items if item.calc_status == "success"),
            }
        )

    return {
        "subject": "stamping_part",
        "part_count": len(rows),
        "success_count": success_count,
        "failed_count": failed_count,
        "unit_cost_sum": money_str(unit_sum),
        "avg_unit_cost": money_str(avg),
        "material_net_sum": money_str(material_sum),
        "process_fee_sum": money_str(process_sum),
        "months": months,
    }


def build_steel_summary(rows: list[SteelMonthlyAvgRow]) -> dict[str, Any]:
    """钢材联动价一览口径的 summary（对齐 #/steel-price-list）。"""
    if not rows:
        return {
            "subject": "steel_price",
            "month_count": 0,
            "row_count": 0,
            "avg_final_price": "0.0000",
            "min_final_price": "0.0000",
            "max_final_price": "0.0000",
            "months": [],
        }

    sorted_rows = sorted(rows, key=lambda row: (row.year, row.month))
    latest = sorted_rows[-1]
    total_rows = sum(row.row_count for row in rows)
    return {
        "subject": "steel_price",
        "month_count": len(rows),
        "row_count": total_rows,
        "avg_final_price": money_str(latest.avg_final_price),
        "min_final_price": money_str(min(row.min_final_price for row in rows)),
        "max_final_price": money_str(max(row.max_final_price for row in rows)),
        "months": [
            {
                "month": month_key(row.year, row.month),
                "location": row.location,
                "avg_final_price": money_str(row.avg_final_price),
                "row_count": row.row_count,
            }
            for row in sorted_rows
        ],
    }
