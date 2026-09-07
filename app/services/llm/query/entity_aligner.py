"""口语实体 → 系统主数据对齐。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.common.part_number import normalize_part_number_token, sanitize_part_number_token
from app.common.tonnage import normalize_tonnage_token
from app.common.vehicle_model import normalize_vehicle_model
from app.repositories.llm.scope_options_repository import ScopeOptionsRepository


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
        alias_map = self._scope_repo.location_alias_map(db)
        vehicles_by_code = self._vehicle_lookup(self._scope_repo.list_vehicle_models(db))
        bom_versions = set(self._scope_repo.list_bom_versions(db))

        filters = dict(seed_filters or {})
        unresolved: list[str] = []

        for key_hint, raw in mentions:
            text = (raw or "").strip()
            if not text:
                continue
            key = key_hint.strip()
            if key == "location":
                aligned = self._align_location(text, locations, alias_map)
                if aligned:
                    filters["location"] = aligned
                else:
                    unresolved.append(f"location:{text}")
            elif key == "vehicle_model":
                cleaned = text.replace("车型", "").replace("项目", "").strip()
                tonnage_token = normalize_tonnage_token(cleaned) or normalize_tonnage_token(text)
                if tonnage_token:
                    filters["tonnage"] = tonnage_token
                    continue
                aligned = self._align_vehicle_model(cleaned, text, vehicles_by_code)
                if aligned:
                    filters["vehicle_model"] = aligned
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

    @staticmethod
    def _vehicle_lookup(names: list[str]) -> dict[str, str]:
        lookup: dict[str, str] = {}
        for name in names:
            text = (name or "").strip()
            if not text:
                continue
            lookup[text] = text
            normalized = normalize_vehicle_model(text)
            if normalized:
                lookup.setdefault(normalized, text)
        return lookup

    @staticmethod
    def _align_vehicle_model(
        cleaned: str,
        original: str,
        vehicles_by_code: dict[str, str],
    ) -> str | None:
        for candidate in (cleaned, original):
            if candidate in vehicles_by_code:
                return vehicles_by_code[candidate]
            normalized = normalize_vehicle_model(candidate)
            if normalized and normalized in vehicles_by_code:
                return vehicles_by_code[normalized]
        return None

    def _align_location(
        self,
        raw: str,
        known: set[str],
        alias_map: dict[str, str],
    ) -> str | None:
        if raw in known:
            return raw
        canonical = alias_map.get(raw)
        if canonical and canonical in known:
            return canonical
        return None
