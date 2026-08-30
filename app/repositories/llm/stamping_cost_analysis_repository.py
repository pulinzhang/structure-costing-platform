"""冲压零件价 — 只读查询。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment
from app.models.costing.stamping_part_cost import StampingPartCost
from app.services.llm._money import ym_int


@dataclass(frozen=True, slots=True)
class StampingPartPeriodRow:
    year: int
    month: int
    part_number: str
    part_name: str | None
    unit_cost: Decimal
    material_net_per_part: Decimal | None
    process_fee_amount: Decimal | None
    calc_status: str
    stamping_supplier: str
    die_fee_amount: Decimal | None = None
    gauge_fee_amount: Decimal | None = None


class StampingCostAnalysisRepository:
    def query_part_rows(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int,
        part_number: str | None = None,
        limit: int = 5000,
    ) -> list[StampingPartPeriodRow]:
        start = ym_int(start_year, start_month)
        end = ym_int(end_year, end_month)
        ym_expr = StampingPartCost.year * 100 + StampingPartCost.month

        q = db.query(StampingPartCost).filter(ym_expr >= start, ym_expr <= end)
        if location:
            q = q.filter(StampingPartCost.location == location)
        if vehicle_model:
            q = q.filter(StampingPartCost.vehicle_model == vehicle_model)
        if part_number:
            pattern = f"%{escape_like_fragment(part_number)}%"
            q = q.filter(StampingPartCost.part_number.like(pattern, escape="\\"))

        q = q.order_by(
            StampingPartCost.year.asc(),
            StampingPartCost.month.asc(),
            StampingPartCost.unit_cost.desc(),
        ).limit(limit)

        rows: list[StampingPartPeriodRow] = []
        for row in q.all():
            rows.append(
                StampingPartPeriodRow(
                    year=int(row.year),
                    month=int(row.month),
                    part_number=str(row.part_number),
                    part_name=row.part_name,
                    unit_cost=Decimal(str(row.unit_cost or 0)),
                    material_net_per_part=(
                        Decimal(str(row.material_net_per_part))
                        if row.material_net_per_part is not None
                        else None
                    ),
                    process_fee_amount=(
                        Decimal(str(row.process_fee_amount))
                        if getattr(row, "process_fee_amount", None) is not None
                        else None
                    ),
                    die_fee_amount=(
                        Decimal(str(row.die_fee_amount))
                        if getattr(row, "die_fee_amount", None) is not None
                        else None
                    ),
                    gauge_fee_amount=(
                        Decimal(str(row.gauge_fee_amount))
                        if getattr(row, "gauge_fee_amount", None) is not None
                        else None
                    ),
                    calc_status=str(row.calc_status or "success"),
                    stamping_supplier=str(row.stamping_supplier),
                )
            )
        return rows
