"""压机吨位口语片段解析（如 40T、80吨）。"""

from __future__ import annotations

import re

_TONNAGE_RE = re.compile(
    r"(?<![0-9])(\d{1,4})\s*(?:[Tt]|吨)(?![0-9A-Za-z])",
)


def extract_tonnage_from_text(text: str) -> int | None:
    match = _TONNAGE_RE.search(text or "")
    if not match:
        return None
    value = int(match.group(1))
    return value if value > 0 else None


def normalize_tonnage_token(value: str) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    if text.isdigit():
        return str(int(text))
    parsed = extract_tonnage_from_text(text)
    return str(parsed) if parsed is not None else None
