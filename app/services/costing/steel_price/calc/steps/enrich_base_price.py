"""Step2：根据基价表补齐钢厂 / 大类 / 基准价 / 溯源。

匹配只认钢厂 + 大类（冷轧 / 镀锌 / 酸洗），与中标厚度一览相同：
材料牌号用来查分类并落库，不对基价表 `grade`。
同一钢厂、同一基准规格若有多条大类基价，只留一条。
每个工艺牌号+料厚各自落一行，供零件核价按牌号取价。
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.services.costing.steel_price.calc.category import resolve_canonical_category
from app.services.costing.steel_price.calc.models import (
    CalcRow,
    MaterialThicknessRow,
    SteelPriceCalcRequest,
)
from app.services.yishiyiyi.base_price.steel_base_price_service import SteelBasePriceService
from app.services.yishiyiyi.steel_grade_category import SteelGradeCategoryService
from app.services.yishiyiyi.steel_grade_category.constants import (
    CANONICAL_CATEGORY_NAMES,
    normalize_category_name,
)


def select_base_records_for_category(candidates: list[Any]) -> list[Any]:
    """同一大类内按钢厂 + 基准厚宽去重；同规格多行取 id 最小的一条。"""
    grouped: dict[tuple[str, str, str], list[Any]] = defaultdict(list)
    for row in candidates:
        mill = (row.steel_mill or "").strip()
        if not mill or row.thick is None or row.width is None:
            continue
        spec_key = (mill, str(row.thick), str(row.width))
        grouped[spec_key].append(row)

    picked: list[Any] = []
    for spec_rows in grouped.values():
        picked.append(min(spec_rows, key=lambda item: int(getattr(item, "id", 0) or 0)))
    return picked


class BasePriceEnricher:
    """
    匹配：档案大类 → 基地 + 大类基价（不按牌号）。
    同一大类可对应多钢厂/规格 → 展开为多行。
    材料行自带 location，必须与基价 location 一致，避免串基地。
    """

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

        category_index: dict[tuple[str, str], list[Any]] = {}
        for location in locations:
            base_records = self.base_price_service.list_for_calc(
                db,
                year=request.year,
                month=request.month,
                location=location,
            )
            for record in base_records:
                record_location = (record.location or "").strip()
                category_name = normalize_category_name(record.category_name)
                if not record_location or category_name not in CANONICAL_CATEGORY_NAMES:
                    continue
                category_index.setdefault((record_location, category_name), []).append(record)

        rows: list[CalcRow] = []
        no_base_count = 0
        no_base_details: list[str] = []

        for material in materials:
            location = material.location
            material_grade = (material.material or "").strip()
            thickness_text = f"{float(material.thickness):.4f}"
            category_name = resolve_canonical_category(material_grade, category_map)

            if not category_name:
                no_base_count += 1
                no_base_details.append(
                    f"[{location}] {material_grade}@{thickness_text} "
                    "未分类，无法按冷轧/镀锌/酸洗匹配基价"
                )
                continue

            candidates = category_index.get((location, category_name), [])
            matches = select_base_records_for_category(candidates)
            if not matches:
                no_base_count += 1
                no_base_details.append(
                    f"[{location}] {material_grade}@{thickness_text} "
                    f"大类={category_name} 无匹配基价"
                )
                continue

            for base in matches:
                base_location = (base.location or "").strip()
                if base_location != location:
                    no_base_count += 1
                    no_base_details.append(
                        f"[{location}] {material_grade}@{thickness_text} "
                        f"基价基地不一致(base={base_location}, id={base.id})"
                    )
                    continue

                if base.width is None or base.thick is None or base.base_price is None:
                    no_base_count += 1
                    no_base_details.append(
                        f"[{location}] {material_grade}@{thickness_text} "
                        f"基价字段不完整(id={base.id})"
                    )
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
