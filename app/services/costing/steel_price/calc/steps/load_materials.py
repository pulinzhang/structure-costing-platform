"""Step1：取出材料厚度列表。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.costing.steel_price.calc.models import MaterialThicknessRow, SteelPriceCalcRequest
from app.services.stamping.part.service import StampingPartService


class MaterialThicknessLoader:
    """从该基地该月仍有效的冲压件取材质（含拼焊子片，不按车型）。"""

    def load(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
    ) -> list[MaterialThicknessRow]:
        scope_location = request.location.strip()
        if not scope_location:
            return []
        raw_rows = StampingPartService().list_materials_as_of(
            db,
            location=scope_location,
            year=request.year,
            month=request.month,
        )
        result: list[MaterialThicknessRow] = []
        seen: set[tuple[str, str, str]] = set()
        for row in raw_rows:
            row_location = (row["location"] or "").strip()
            material = (row["material"] or "").strip()
            thickness = row["thickness"]
            if not row_location or not material or thickness is None:
                continue
            thickness_decimal = Decimal(str(thickness))
            unique_key = (row_location, material, str(thickness_decimal))
            if unique_key in seen:
                continue
            seen.add(unique_key)
            result.append(
                MaterialThicknessRow(
                    location=row_location,
                    material=material,
                    thickness=thickness_decimal,
                )
            )
        return result
