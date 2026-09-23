"""Step2：按中标厚度一览同一套规则取基价——基价表牌号命中，用该行自己的基准价。

牌号比对：去空格后全等，字母 O 与数字 0 视为同一字符（Excel 常见 DCO3 / DCO4）。
不按冷轧/镀锌/酸洗大类把别的牌号基准价摊过来。
缺牌号按基地+牌号各报一条，同一牌号的不同厚度不重复计数。
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.steel_grade import grade_match_key
from app.models.yishiyiyi import SteelBasePrice
from app.services.costing.steel_price.calc.category import resolve_canonical_category
from app.services.costing.steel_price.calc.models import (
    CalcRow,
    MaterialThicknessRow,
    SteelPriceCalcRequest,
)
from app.services.masterdata.steel_grade_category.service import (
    SteelGradeCategoryService,
)
from app.services.yishiyiyi.base_price.service import SteelBasePriceService
from app.services.yishiyiyi.winning_thickness.assemble.row_assembler import (
    dedupe_bases_by_mill_grade,
)


def select_winning_base_records(
    candidates: Sequence[SteelBasePrice],
    material_grade: str,
) -> list[SteelBasePrice]:
    """与一览表相同：牌号命中后按牌号+钢厂去重。O/0 视为同一字符。"""
    wanted = grade_match_key(material_grade)
    if not wanted:
        return []
    matched = [row for row in candidates if grade_match_key(row.grade) == wanted]
    return dedupe_bases_by_mill_grade(matched)


def note_grade_gap(
    seen: set[tuple[str, str, str]],
    details: list[str],
    *,
    location: str,
    grade: str,
    reason: str,
    detail: str,
) -> bool:
    """同一基地、同一牌号、同一原因只记一条。厚度不参与基价是否命中。"""
    key = ((location or "").strip(), grade_match_key(grade), reason)
    if key in seen:
        return False
    seen.add(key)
    details.append(detail)
    return True


class BasePriceEnricher:
    """基地 + 基价表牌号；同一牌号多钢厂展开为多行。"""

    def __init__(self) -> None:
        self.base_price_service = SteelBasePriceService()
        self._grade_category_service = SteelGradeCategoryService()

    def enrich(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
        materials: list[MaterialThicknessRow],
    ) -> tuple[list[CalcRow], int, list[str]]:
        locations = sorted({m.location for m in materials if m.location})
        if not locations and request.location:
            locations = [request.location]

        grades = [
            (item.material or "").strip() for item in materials if (item.material or "").strip()
        ]
        category_map = self._grade_category_service.map_grades(db, grades)

        bases_by_location: dict[str, list[SteelBasePrice]] = {}
        for location in locations:
            bases_by_location[location] = self.base_price_service.list_for_calc(
                db,
                year=request.year,
                month=request.month,
                location=location,
            )

        rows: list[CalcRow] = []
        no_base_count = 0
        no_base_details: list[str] = []
        seen_grade_gaps: set[tuple[str, str, str]] = set()

        for material in materials:
            location = material.location
            material_grade = (material.material or "").strip()
            category_name = resolve_canonical_category(material_grade, category_map)

            if not category_name:
                if note_grade_gap(
                    seen_grade_gaps,
                    no_base_details,
                    location=location,
                    grade=material_grade,
                    reason="unclassified",
                    detail=(
                        f"[{location}] {material_grade} " "未分类，无法按冷轧/镀锌/酸洗匹配基价"
                    ),
                ):
                    no_base_count += 1
                continue

            matches = select_winning_base_records(
                bases_by_location.get(location, []),
                material_grade,
            )
            if not matches:
                if note_grade_gap(
                    seen_grade_gaps,
                    no_base_details,
                    location=location,
                    grade=material_grade,
                    reason="missing_grade",
                    detail=(
                        f"[{location}] {material_grade} " f"大类={category_name} 基价表无该牌号"
                    ),
                ):
                    no_base_count += 1
                continue

            for base in matches:
                base_location = (base.location or "").strip()
                if base_location != location:
                    if note_grade_gap(
                        seen_grade_gaps,
                        no_base_details,
                        location=location,
                        grade=material_grade,
                        reason=f"location:{base.id}",
                        detail=(
                            f"[{location}] {material_grade} "
                            f"基价基地不一致(base={base_location}, id={base.id})"
                        ),
                    ):
                        no_base_count += 1
                    continue

                rows.append(
                    CalcRow(
                        year=request.year,
                        month=request.month,
                        location=location,
                        grade=material_grade,
                        thickness=material.thickness,
                        steel_mill=base.steel_mill,
                        category_name=category_name,
                        width=Decimal(str(base.width)),
                        base_thickness=Decimal(str(base.thick)),
                        base_price=Decimal(str(base.base_price)),
                        processing_fee=Decimal(str(base.processing_fee or 0)),
                        base_price_id=base.id,
                        base_excel_filename=base.excel_filename,
                        base_sheet_name=base.sheet_name,
                        base_excel_row=base.excel_row,
                        base_excel_col=base.excel_col,
                        match_status="base_only",
                        calc_status="partial",
                    )
                )

        return rows, no_base_count, no_base_details
