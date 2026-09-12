"""幂等键与问题指纹。"""

from __future__ import annotations

import hashlib
import re

_WS_RE = re.compile(r"\s+")


def normalize_question(text: str) -> str:
    return _WS_RE.sub(" ", (text or "").strip()).lower()


def question_fingerprint(text: str) -> str:
    normalized = normalize_question(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def build_idempotency_key(
    *,
    report_type: str,
    audience: str,
    location: str,
    year: int,
    month: int,
    vehicle_model: str,
    bom_version: str,
    user_question: str,
    user_id: int,
    part_number: str | None = None,
) -> str:
    q_fp = question_fingerprint(user_question)
    part = (part_number or "").strip()
    part_seg = f"|pn:{part}" if part else ""
    return (
        f"{report_type}|{audience}|{location}|{year}|{month}|"
        f"{vehicle_model}|{bom_version}{part_seg}|q:{q_fp}|user:{user_id}"
    )
