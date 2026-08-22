"""中标钢厂厚度价格一览 — LLM 只读查询（复用行组装）。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.yishiyiyi.winning_thickness import WinningThicknessExportService


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


class WinningThicknessAnalysisRepository:
    def __init__(self) -> None:
        self._export_service = WinningThicknessExportService()

    def query_rows(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
        limit: int = 8000,
    ) -> list[WinningThicknessAnalysisRow]:
        location_text = (location or "").strip()
        if not location_text:
            return []

        vos = self._export_service.build_rows(
            db,
            year=year,
            month=month,
            location=location_text,
            steel_mill=steel_mill,
            category_name=category_name,
            grade=grade,
        )
        rows: list[WinningThicknessAnalysisRow] = []
        for row in vos[:limit]:
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
