"""中标厚度价 summary / drivers。"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from app.repositories.llm.winning_thickness_analysis_repository import (
    WinningThicknessAnalysisRow,
)
from app.services.llm._money import money_str, month_key


def build_winning_thickness_summary(rows: list[WinningThicknessAnalysisRow]) -> dict[str, Any]:
    if not rows:
        return {
            "subject": "winning_thickness",
            "row_count": 0,
            "steel_mill_count": 0,
            "category_count": 0,
            "avg_final_price": "0.0000",
            "months": [],
        }

    mills = {row.steel_mill for row in rows}
    categories = {row.category_name for row in rows}
    final_sum = sum((row.final_price for row in rows), start=Decimal("0"))
    count = Decimal(len(rows))
    by_month: dict[str, int] = defaultdict(int)
    for row in rows:
        by_month[month_key(row.year, row.month)] += 1

    return {
        "subject": "winning_thickness",
        "row_count": len(rows),
        "steel_mill_count": len(mills),
        "category_count": len(categories),
        "avg_final_price": money_str(final_sum / count),
        "months": [
            {"month": month, "row_count": row_count}
            for month, row_count in sorted(by_month.items())
        ],
    }


def build_winning_thickness_drivers(
    rows: list[WinningThicknessAnalysisRow],
    *,
    top_n: int = 15,
) -> dict[str, Any]:
    """按钢厂汇总厚度阶梯行数。"""
    by_mill: dict[str, list[WinningThicknessAnalysisRow]] = defaultdict(list)
    for row in rows:
        by_mill[row.steel_mill].append(row)

    items: list[dict[str, Any]] = []
    for mill, mill_rows in by_mill.items():
        finals = [row.final_price for row in mill_rows]
        items.append(
            {
                "object_type": "winning_thickness",
                "steel_mill": mill,
                "row_count": len(mill_rows),
                "max_final_price": money_str(max(finals)),
                "min_final_price": money_str(min(finals)),
            }
        )

    ranked = sorted(items, key=lambda item: item["row_count"], reverse=True)[:top_n]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {"kind": "drivers", "items": ranked, "top_n": top_n}
