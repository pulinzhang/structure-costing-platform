"""口语实体 → 系统主数据对齐。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.common.part_number import normalize_part_number_token, sanitize_part_number_token
from app.common.tonnage import normalize_tonnage_token
from app.repositories.llm.scope_options_repository import ScopeOptionsRepository

_LOCATION_ALIASES = {
    "青岛厂": "青岛",
    "青岛基地": "青岛",
    "芜湖厂": "芜湖",
    "芜湖基地": "芜湖",
    "大连厂": "大连",
    "大连基地": "大连",
    "鄂尔多斯基地": "鄂尔多斯",
}


@dataclass(frozen=True, slots=True)
class AlignResult:
    filters: dict[str, str]
    unresolved_mentions: list[str]


class EntityAligner:
    def __init__(self) -> None:
        self._scope_repo = ScopeOptionsRepository()

    def align(
        self,
        db: Session,
        *,
        mentions: list[tuple[str, str]],
        seed_filters: dict[str, str] | None = None,
    ) -> AlignResult:
        """
        mentions: (key_hint, raw_text)
        """
        locations = set(self._scope_repo.list_locations(db))
        vehicles = set(self._scope_repo.list_vehicle_models(db))
        bom_versions = set(self._scope_repo.list_bom_versions(db))

        filters = dict(seed_filters or {})
        unresolved: list[str] = []

        for key_hint, raw in mentions:
            text = (raw or "").strip()
            if not text:
                continue
            key = key_hint.strip()
            if key == "location":
                aligned = self._align_location(text, locations)
                if aligned:
                    filters["location"] = aligned
                else:
                    unresolved.append(f"location:{text}")
            elif key == "vehicle_model":
                cleaned = text.replace("车型", "").strip()
                tonnage_token = normalize_tonnage_token(cleaned) or normalize_tonnage_token(text)
                if tonnage_token:
                    filters["tonnage"] = tonnage_token
                    continue
                if cleaned in vehicles:
                    filters["vehicle_model"] = cleaned
                elif text in vehicles:
                    filters["vehicle_model"] = text
                else:
                    unresolved.append(f"vehicle_model:{text}")
            elif key == "bom_version":
                if text in bom_versions:
                    filters["bom_version"] = text
                else:
                    unresolved.append(f"bom_version:{text}")
            elif key == "part_number":
                token = sanitize_part_number_token(text)
                if not token:
                    continue
                matches = self._scope_repo.list_part_numbers_matching(db, token)
                if len(matches) == 1:
                    filters["part_number"] = matches[0]
                else:
                    filters["part_number"] = token
                if len(matches) > 1 and token not in {
                    normalize_part_number_token(m) for m in matches
                }:
                    unresolved.append(f"part_number:{text}")
            elif key == "tonnage":
                tonnage_token = normalize_tonnage_token(text)
                if tonnage_token:
                    filters["tonnage"] = tonnage_token
                else:
                    unresolved.append(f"tonnage:{text}")
            else:
                filters[key] = text

        return AlignResult(filters=filters, unresolved_mentions=unresolved)

    def _align_location(self, raw: str, known: set[str]) -> str | None:
        if raw in known:
            return raw
        alias = _LOCATION_ALIASES.get(raw)
        if alias and alias in known:
            return alias
        if alias:
            return alias
        for suffix in ("厂", "基地"):
            if raw.endswith(suffix):
                base = raw[: -len(suffix)]
                if base in known:
                    return base
        for location in known:
            if location in raw or raw in location:
                return location
        return None
