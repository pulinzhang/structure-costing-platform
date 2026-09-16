"""幂等键与问题指纹。"""

from __future__ import annotations

import hashlib
import json
import re

_WS_RE = re.compile(r"\s+")


def normalize_question(text: str) -> str:
    return _WS_RE.sub(" ", (text or "").strip()).lower()


def question_fingerprint(text: str) -> str:
    normalized = normalize_question(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def filters_fingerprint(filters: dict[str, str] | None) -> str:
    items = sorted((str(key), str(value)) for key, value in (filters or {}).items() if value)
    blob = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def build_idempotency_key(
    *,
    report_type: str,
    audience: str,
    user_question: str,
    user_id: int,
    time_range_start: str,
    time_range_end: str,
    filters: dict[str, str] | None = None,
) -> str:
    q_fp = question_fingerprint(user_question)
    return (
        f"{report_type}|{audience}|{time_range_start}|{time_range_end}|"
        f"f:{filters_fingerprint(filters)}|q:{q_fp}|user:{user_id}"
    )
