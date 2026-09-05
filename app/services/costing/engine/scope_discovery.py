"""核价引擎 — 范围发现。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.repositories.bom.bom_repository import BomSnapshotRepository
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
    vehicle_models: list[str] = field(default_factory=list)
    l0_scopes: list[L0Scope] = field(default_factory=list)


class ScopeDiscovery:
    """发现配套车型与全部含 L0 的 BOM 版本。"""

    def __init__(self) -> None:
        self.part_repo = StampingPartRepository()
        self.bom_snapshot_repo = BomSnapshotRepository()

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
        vehicle_models: list[str] = []
        for alias in aliases:
            options = self.part_repo.get_cascade_filter_options(db, location=alias)
            for name in options.get("vehicle_models") or []:
                model = (name or "").strip()
                if model and model not in vehicle_models:
                    vehicle_models.append(model)

        l0_scopes = [
            L0Scope(
                location=row["location"],
                vehicle_model=row["vehicle_model"],
                bom_version=row["bom_version"],
            )
            for row in self.bom_snapshot_repo.discover_l0_scopes(db, aliases)
        ]
        return DiscoveryResult(
            location=location_clean,
            year=year,
            month=month,
            location_aliases=aliases,
            vehicle_models=vehicle_models,
            l0_scopes=l0_scopes,
        )
