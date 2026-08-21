"""核价引擎 — 范围发现。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.bom import BomNode, BomSnapshot
from app.repositories.stamping.stamping_part_repository import StampingPartRepository
from app.services.costing.stamping_part_cost.helpers import location_candidates


@dataclass(frozen=True)
class L0Scope:
    vehicle_model: str
    bom_version: str
    location: str  # 快照上实际 location 字符串


@dataclass
class DiscoveryResult:
    location: str
    year: int
    month: int
    location_aliases: list[str] = field(default_factory=list)
    stamping_suppliers: list[str] = field(default_factory=list)
    l0_scopes: list[L0Scope] = field(default_factory=list)


class ScopeDiscovery:
    """发现工厂与全部含 L0 的 BOM 版本。"""

    def __init__(self) -> None:
        self.part_repo = StampingPartRepository()

    def discover(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        month: int,
    ) -> DiscoveryResult:
        location_clean = (location or "").strip()
        aliases = location_candidates(location_clean)
        suppliers: list[str] = []
        for alias in aliases:
            options = self.part_repo.get_cascade_filter_options(db, location=alias)
            for supplier in options.get("stamping_suppliers") or []:
                name = (supplier or "").strip()
                if name and name not in suppliers:
                    suppliers.append(name)

        l0_scopes = self._discover_l0_scopes(db, aliases)
        return DiscoveryResult(
            location=location_clean,
            year=year,
            month=month,
            location_aliases=aliases,
            stamping_suppliers=suppliers,
            l0_scopes=l0_scopes,
        )

    def _discover_l0_scopes(
        self,
        db: Session,
        aliases: list[str],
    ) -> list[L0Scope]:
        if not aliases:
            return []
        rows = (
            db.query(
                BomSnapshot.location,
                BomSnapshot.vehicle_model,
                BomSnapshot.bom_version,
            )
            .join(BomNode, BomNode.snapshot_id == BomSnapshot.id)
            .filter(
                BomSnapshot.location.in_(aliases),
                BomNode.level == 0,
            )
            .group_by(
                BomSnapshot.location,
                BomSnapshot.vehicle_model,
                BomSnapshot.bom_version,
            )
            .having(func.count(BomNode.id) > 0)
            .order_by(
                BomSnapshot.vehicle_model,
                BomSnapshot.bom_version,
            )
            .all()
        )
        scopes: list[L0Scope] = []
        seen: set[tuple[str, str]] = set()
        for location, vehicle_model, bom_version in rows:
            key = ((vehicle_model or "").strip(), (bom_version or "").strip())
            if not key[0] or not key[1] or key in seen:
                continue
            seen.add(key)
            scopes.append(
                L0Scope(
                    location=(location or "").strip(),
                    vehicle_model=key[0],
                    bom_version=key[1],
                )
            )
        return scopes
