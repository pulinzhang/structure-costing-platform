"""Scope 下拉：只读主数据与结果表，不经上游 Service。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.part_number import escape_like_fragment
from app.models.costing.assembly_cost import AssemblyCost
from app.models.costing.stamping_part_cost import StampingPartCost
from app.models.costing.steel_price import SteelPrice
from app.models.masterdata.location import Location, LocationAlias
from app.models.masterdata.vehicle_model import VehicleModel
from app.models.stamping.part import StampingPart


class ScopeOptionsRepository:
    def list_locations(self, db: Session) -> list[str]:
        rows = (
            db.query(Location.location)
            .order_by(Location.sort_order.asc(), Location.location.asc())
            .all()
        )
        return [str(name).strip() for (name,) in rows if name]

    def location_alias_map(self, db: Session) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for (name,) in db.query(Location.location).all():
            text = str(name).strip() if name else ""
            if text:
                mapping[text] = text
        for alias, canonical in db.query(LocationAlias.alias, LocationAlias.location).all():
            alias_text = str(alias).strip() if alias else ""
            canonical_text = str(canonical).strip() if canonical else ""
            if alias_text and canonical_text:
                mapping[alias_text] = canonical_text
        return mapping

    def expand_location_names(self, db: Session, raw: str) -> list[str]:
        text = (raw or "").strip()
        if not text:
            return []
        mapping = self.location_alias_map(db)
        canonical = mapping.get(text)
        if canonical is None:
            return []
        names = [canonical]
        for alias, location in mapping.items():
            if location == canonical and alias not in names:
                names.append(alias)
        return names

    def list_vehicle_models(self, db: Session) -> list[str]:
        rows = (
            db.query(VehicleModel.vehicle_model)
            .distinct()
            .order_by(VehicleModel.vehicle_model.asc())
            .all()
        )
        return [str(code).strip() for (code,) in rows if code]

    def list_bom_versions(self, db: Session) -> list[str]:
        rows = db.query(AssemblyCost.bom_version).distinct().all()
        return sorted(str(item[0]).strip() for item in rows if item[0])

    def list_years(self, db: Session) -> list[int]:
        values: set[int] = set()
        for rows in (
            db.query(AssemblyCost.year).distinct().all(),
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
            db.query(AssemblyCost.part_number)
            .filter(AssemblyCost.part_number.like(pattern, escape="\\"))
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
