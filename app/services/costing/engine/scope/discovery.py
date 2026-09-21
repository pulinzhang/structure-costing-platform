"""核价引擎 — 范围发现。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.repositories.bom.bom.snapshot import BomSnapshotRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.vehicle_model.service import VehicleModelService


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
    as_of_vehicle_models: list[str] = field(default_factory=list)

    def is_period_filtered(self) -> bool:
        return bool(self.as_of_vehicle_models) and not self.vehicle_models


class ScopeDiscovery:
    """本期名单 = 该月命中的冲压零件 ∪ 命中 L0，再按项目档案月命中裁掉停产/未投产。"""

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
        l0_scopes = self._list_l0_scopes(db, aliases=aliases, year=year, month=month)
        stamping_vehicle_models = self._list_stamping_vehicle_models(
            db, aliases=aliases, year=year, month=month
        )
        vehicle_models = sorted(
            set(stamping_vehicle_models) | {scope.vehicle_model for scope in l0_scopes}
        )
        allowed = set(self.vehicle_model_service.list_introducible(db, location_clean, year, month))
        stamping_vehicle_models = [code for code in stamping_vehicle_models if code in allowed]
        l0_scopes = [scope for scope in l0_scopes if scope.vehicle_model in allowed]
        filtered = sorted(
            set(stamping_vehicle_models) | {scope.vehicle_model for scope in l0_scopes}
        )
        return DiscoveryResult(
            location=location_clean,
            year=year,
            month=month,
            location_aliases=aliases,
            vehicle_models=filtered,
            stamping_vehicle_models=stamping_vehicle_models,
            l0_scopes=l0_scopes,
            as_of_vehicle_models=vehicle_models,
        )

    def _list_l0_scopes(
        self,
        db: Session,
        *,
        aliases: list[str],
        year: int,
        month: int,
    ) -> list[L0Scope]:
        if not aliases:
            return []
        l0_scopes: list[L0Scope] = []
        seen: set[tuple[str, str]] = set()
        for row in self.bom_snapshot_repo.discover_l0_scopes(
            db, aliases, as_of_year=year, as_of_month=month
        ):
            code = self.vehicle_model_service.normalize(row["vehicle_model"])
            version = (row["bom_version"] or "").strip()
            if not code or not version:
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
        return l0_scopes

    def _list_stamping_vehicle_models(
        self,
        db: Session,
        *,
        aliases: list[str],
        year: int,
        month: int,
    ) -> list[str]:
        if not aliases:
            return []
        options = self.part_repo.get_cascade_filter_options(
            db, locations=aliases, as_of_year=year, as_of_month=month
        )
        names: list[str] = []
        seen: set[str] = set()
        for raw in options.get("vehicle_models") or []:
            code = self.vehicle_model_service.normalize(str(raw).strip() if raw else "")
            if not code or code in seen:
                continue
            seen.add(code)
            names.append(code)
        return names
