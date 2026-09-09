"""核价引擎 — 范围发现。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.repositories.bom.bom_repository import BomSnapshotRepository
from app.repositories.stamping.stamping_part_repository import StampingPartRepository
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.vehicle_model import VehicleModelService


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
    stamping_vehicle_models: list[str] = field(default_factory=list)
    l0_scopes: list[L0Scope] = field(default_factory=list)


class ScopeDiscovery:
    """本期项目名单来自项目主数据；L0Scope 再按该名单过滤。"""

    def __init__(self) -> None:
        self.bom_snapshot_repo = BomSnapshotRepository()
        self.part_repo = StampingPartRepository()
        self.vehicle_model_service = VehicleModelService()

    def discover(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        month: int,
    ) -> DiscoveryResult:
        location_clean = (location or "").strip()
        aliases = LocationService().expand_for_query(db, location_clean)
        vehicle_models = self.vehicle_model_service.list_introducible(
            db, location_clean, year, month
        )
        allowed = set(vehicle_models)

        l0_scopes: list[L0Scope] = []
        seen: set[tuple[str, str]] = set()
        if aliases and allowed:
            for row in self.bom_snapshot_repo.discover_l0_scopes(db, aliases):
                code = self.vehicle_model_service.normalize(row["vehicle_model"])
                version = (row["bom_version"] or "").strip()
                if not code or not version or code not in allowed:
                    continue
                key = (code, version)
                if key in seen:
                    continue
                seen.add(key)
                l0_scopes.append(
                    L0Scope(
                        location=row["location"],
                        vehicle_model=code,
                        bom_version=version,
                    )
                )
        stamping_vehicle_models = self._list_stamping_vehicle_models(
            db, aliases=aliases, vehicle_models=vehicle_models
        )
        return DiscoveryResult(
            location=location_clean,
            year=year,
            month=month,
            location_aliases=aliases,
            vehicle_models=vehicle_models,
            stamping_vehicle_models=stamping_vehicle_models,
            l0_scopes=l0_scopes,
        )

    def _list_stamping_vehicle_models(
        self,
        db: Session,
        *,
        aliases: list[str],
        vehicle_models: list[str],
    ) -> list[str]:
        if not aliases or not vehicle_models:
            return []
        options = self.part_repo.get_cascade_filter_options(db, locations=aliases)
        present = {str(name).strip() for name in (options.get("vehicle_models") or []) if name}
        return [name for name in vehicle_models if name in present]
