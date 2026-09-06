"""模具布点身份筛选（供应商 / 版本）。"""

from __future__ import annotations

from app.common.scrap_byproduct import layout_is_scrap_byproduct_part
from app.models.stamping.die import StampingDiePart
from app.services.stamping.die.process_identity import matches_die_identity


def die_part_identity_key(part: StampingDiePart) -> tuple[str, str, str]:
    return (
        (part.stamping_supplier or "").strip(),
        (part.version or "").strip(),
        (part.part_number or "").strip(),
    )


def is_scrap_byproduct_die_part(
    part: StampingDiePart,
    scrap_keys: frozenset[tuple[str, str, str]],
) -> bool:
    if die_part_identity_key(part) in scrap_keys:
        return True
    return layout_is_scrap_byproduct_part(part)


def strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def matches_part(
    part: StampingDiePart,
    *,
    stamping_supplier: str | None,
    version: str | None,
) -> bool:
    return matches_die_identity(
        part.stamping_supplier,
        part.version,
        stamping_supplier=stamping_supplier,
        version=version,
    )


def parts_for_identity(
    parts: list[StampingDiePart],
    *,
    stamping_supplier: str | None,
    version: str | None,
) -> list[StampingDiePart]:
    return [
        part
        for part in parts
        if matches_part(part, stamping_supplier=stamping_supplier, version=version)
    ]
