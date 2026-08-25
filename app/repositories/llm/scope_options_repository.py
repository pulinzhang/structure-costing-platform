"""Scope 下拉：从结果表 DISTINCT，不经上游 Service。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.costing.l0_assembly_cost import L0AssemblyCost
from app.models.costing.steel_price import SteelPrice
from app.models.costing.stamping_part_cost import StampingPartCost
from app.models.stamping.part import StampingPart
from app.common.part_number import escape_like_fragment


class ScopeOptionsRepository:
    def list_locations(self, db: Session) -> list[str]:
        values: set[str] = set()
        for rows in (
            db.query(L0AssemblyCost.location).distinct().all(),
            db.query(StampingPartCost.location).distinct().all(),
            db.query(SteelPrice.location).distinct().all(),
        ):
            for (location,) in rows:
                if location:
                    values.add(str(location).strip())
        return sorted(values)

    def list_vehicle_models(self, db: Session) -> list[str]:
        values: set[str] = set()
        for rows in (
            db.query(L0AssemblyCost.vehicle_model).distinct().all(),
            db.query(StampingPartCost.vehicle_model).distinct().all(),
        ):
            for (vehicle_model,) in rows:
                if vehicle_model:
                    values.add(str(vehicle_model).strip())
        return sorted(values)

    def list_bom_versions(self, db: Session) -> list[str]:
        rows = db.query(L0AssemblyCost.bom_version).distinct().all()
        return sorted(str(item[0]).strip() for item in rows if item[0])

    def list_years(self, db: Session) -> list[int]:
        values: set[int] = set()
        for rows in (
            db.query(L0AssemblyCost.year).distinct().all(),
            db.query(StampingPartCost.year).distinct().all(),
            db.query(SteelPrice.year).distinct().all(),
        ):
            for (year,) in rows:
                if year is not None:
                    values.add(int(year))
        return sorted(values, reverse=True)

    def list_part_numbers_matching(
        self,
        db: Session,
        fragment: str,
        *,
        limit: int = 20,
    ) -> list[str]:
        token = escape_like_fragment(fragment).upper()
        if not token:
            return []
        pattern = f"%{token}%"
        values: set[str] = set()
        for rows in (
            db.query(StampingPart.part_number)
            .filter(StampingPart.part_number.like(pattern, escape="\\"))
            .distinct()
            .limit(limit)
            .all(),
            db.query(L0AssemblyCost.part_number)
            .filter(L0AssemblyCost.part_number.like(pattern, escape="\\"))
            .distinct()
            .limit(limit)
            .all(),
            db.query(StampingPartCost.part_number)
            .filter(StampingPartCost.part_number.like(pattern, escape="\\"))
            .distinct()
            .limit(limit)
            .all(),
        ):
            for (part_number,) in rows:
                if part_number:
                    values.add(str(part_number).strip())
        return sorted(values)[:limit]
