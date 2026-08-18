"""Step1：取出材料厚度列表。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.stamping.stamping_service import StampingPartService
from app.services.costing.steel_price.calc.models import MaterialThicknessRow, SteelPriceCalcRequest


class MaterialThicknessLoader:
    """从冲压件规格去重得到 基地 + 材料(钢种) + 厚度（含拼焊子片）。"""

    def __init__(self) -> None:
        self.stamping_service = StampingPartService()

    def load(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
    ) -> list[MaterialThicknessRow]:
        raw_rows = self.stamping_service.list_material_specs(
            db,
            location=request.location,
            stamping_supplier=request.stamping_supplier,
            vehicle_model=request.vehicle_model,
        )
        result: list[MaterialThicknessRow] = []
        for row in raw_rows:
            location = (row.get("location") or "").strip()
            material = (row.get("material") or "").strip()
            thickness = row.get("thickness")
            if not location or not material or thickness is None:
                continue
            # 请求指定了基地时，拒绝串入其它基地
            if request.location and location != request.location.strip():
                continue
            result.append(
                MaterialThicknessRow(
                    location=location,
                    material=material,
                    thickness=Decimal(str(thickness)),
                )
            )
        return result
