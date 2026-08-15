"""Step2：根据基价表补齐钢厂 / 大类 / 基准价 / 溯源。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.yishiyiyi.base_price.steel_base_price_service import SteelBasePriceService
from app.services.costing.steel_price.calc.models import (
    CalcRow,
    MaterialThicknessRow,
    SteelPriceCalcRequest,
)


class BasePriceEnricher:
    """
    匹配键：year + month + location(基地) + grade(=material)
    同一牌号可对应多条基价（不同钢厂/规格）→ 展开为多行。
    材料行自带 location，必须与基价 location 一致，避免串基地。
    """

    def __init__(self) -> None:
        self.base_price_service = SteelBasePriceService()

    def enrich(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
        materials: list[MaterialThicknessRow],
    ) -> tuple[list[CalcRow], int, list[str]]:
        locations = sorted({m.location for m in materials if m.location})
        if not locations and request.location:
            locations = [request.location]

        # 按基地分别加载基价，索引键 = (location, grade)
        grade_index: dict[tuple[str, str], list] = {}
        for location in locations:
            base_records = self.base_price_service.list_for_calc(
                db,
                year=request.year,
                month=request.month,
                location=location,
            )
            for record in base_records:
                record_location = (record.location or "").strip()
                key_grade = (record.grade or "").strip()
                if not record_location or not key_grade:
                    continue
                grade_index.setdefault((record_location, key_grade), []).append(record)

        rows: list[CalcRow] = []
        no_base_count = 0
        no_base_details: list[str] = []

        for material in materials:
            location = material.location
            matches = grade_index.get((location, material.material), [])
            if not matches:
                no_base_count += 1
                no_base_details.append(
                    f"[{location}] {material.material}@{float(material.thickness):.4f} 无匹配基价"
                )
                continue

            for base in matches:
                base_location = (base.location or "").strip()
                if base_location != location:
                    no_base_count += 1
                    no_base_details.append(
                        f"[{location}] {material.material}@{float(material.thickness):.4f} "
                        f"基价基地不一致(base={base_location}, id={base.id})"
                    )
                    continue

                if base.width is None or base.thick is None or base.base_price is None:
                    no_base_count += 1
                    no_base_details.append(
                        f"[{location}] {material.material}@{float(material.thickness):.4f} "
                        f"基价字段不完整(id={base.id})"
                    )
                    continue

                rows.append(
                    CalcRow(
                        year=request.year,
                        month=request.month,
                        location=location,
                        grade=material.material,
                        thickness=material.thickness,
                        steel_mill=base.steel_mill,
                        category_name=base.category_name,
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
