"""中标厚度价：调上游导出 Service 取行，再算 summary / drivers。"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.schemas.llm.analysis_payload import (
    DriverItem,
    DriversPayload,
    SummaryPayload,
)
from app.services.llm._money import money_str, month_key
from app.services.yishiyiyi.winning_thickness.export.service import (
    WinningThicknessExportService,
)

_MAX_ROWS = 8000


@dataclass(frozen=True, slots=True)
class WinningThicknessAnalysisRow:
    year: int
    month: int
    location: str
    steel_mill: str
    category_name: str
    grade: str
    thickness_range: str
    base_price: Decimal
    thickness_adjustment: Decimal
    processing_fee: Decimal
    final_price: Decimal


def load_winning_thickness_rows(
    export_service: WinningThicknessExportService,
    db: Session,
    *,
    year: int,
    month: int,
    location: str,
    steel_mill: str | None = None,
    category_name: str | None = None,
    grade: str | None = None,
) -> list[WinningThicknessAnalysisRow]:
    """下游 Analysis 调上游 Service；不经本切片 Repository。"""
    location_text = (location or "").strip()
    if not location_text:
        return []

    vos = export_service.build_rows(
        db,
        year=year,
        month=month,
        location=location_text,
        steel_mill=steel_mill,
        category_name=category_name,
        grade=grade,
    )
    rows: list[WinningThicknessAnalysisRow] = []
    for row in vos[:_MAX_ROWS]:
        rows.append(
            WinningThicknessAnalysisRow(
                year=int(row.year),
                month=int(row.month),
                location=str(row.location),
                steel_mill=str(row.steel_mill),
                category_name=str(row.category_name),
                grade=str(row.grade),
                thickness_range=str(row.thickness_range),
                base_price=Decimal(str(row.base_price)),
                thickness_adjustment=Decimal(str(row.thickness_adjustment)),
                processing_fee=Decimal(str(row.processing_fee)),
                final_price=Decimal(str(row.final_price)),
            )
        )
    return rows


def build_winning_thickness_summary(rows: list[WinningThicknessAnalysisRow]) -> SummaryPayload:
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
) -> DriversPayload:
    """按钢厂汇总厚度阶梯行数。"""
    by_mill: dict[str, list[WinningThicknessAnalysisRow]] = defaultdict(list)
    for row in rows:
        by_mill[row.steel_mill].append(row)

    items: list[DriverItem] = []
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

    ranked = sorted(items, key=lambda item: int(str(item["row_count"])), reverse=True)[:top_n]
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index
    return {"kind": "drivers", "items": ranked, "top_n": top_n}
