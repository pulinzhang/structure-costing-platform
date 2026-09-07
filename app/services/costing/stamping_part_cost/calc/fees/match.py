"""费用档案匹配用的基地 / 项目别名（各费用种类共用匹配，不共用公式）。"""

from __future__ import annotations

from app.common.vehicle_model import normalize_vehicle_model


def vehicle_model_candidates(vehicle_model: str) -> list[str]:
    raw = (vehicle_model or "").strip()
    if not raw:
        return []
    candidates = [raw]
    normalized = normalize_vehicle_model(raw)
    if normalized and normalized != raw:
        candidates.append(normalized)
    return list(dict.fromkeys(candidates))


def location_and_vehicle_keys(
    *,
    locations: list[str],
    vehicle_model: str,
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for loc in locations:
        for vehicle in vehicle_model_candidates(vehicle_model):
            pairs.append((loc, vehicle))
    return pairs
