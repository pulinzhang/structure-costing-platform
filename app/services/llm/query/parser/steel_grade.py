"""问句里的牌号候选与料厚。牌号是否成立由档案查询确认，不在这里查库。"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

# DC01、DC51D+Z、HC180YD+Z、SWRCH22A。OP10 也会命中，须再对档案。
_GRADE_CANDIDATE_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z]{1,12}\d{2,4}[A-Za-z0-9]*(?:\+[A-Za-z0-9]+)?)(?![A-Za-z0-9])"
)
_EXPLICIT_THICKNESS_RE = re.compile(
    r"(?:料厚|厚度)\s*[:：]?\s*(\d+(?:\.\d+)?)"
    r"|(\d+(?:\.\d+)?)\s*(?:mm|毫米)"
    r"|(\d+(?:\.\d+)?)\s*厚"
)
_EACH_THICKNESS_WORDS: tuple[str, ...] = (
    "各厚度",
    "每个厚度",
    "所有厚度",
    "各种厚度",
)
_THICKNESS_MAX = Decimal("20")


def extract_grade_candidates(question: str) -> list[str]:
    """从左到右抽出像牌号的词，不去重以外的加工。"""
    seen: set[str] = set()
    found: list[str] = []
    for match in _GRADE_CANDIDATE_RE.finditer(question or ""):
        token = match.group(1)
        key = token.upper()
        if key in seen:
            continue
        seen.add(key)
        found.append(token)
    return found


def asks_each_thickness(question: str) -> bool:
    text = question or ""
    return any(word in text for word in _EACH_THICKNESS_WORDS)


def extract_thickness(question: str, grade: str) -> str | None:
    """料厚写成不带多余尾零的数字字符串。各厚度不限料厚。"""
    if asks_each_thickness(question):
        return None
    explicit = _explicit_thickness(question)
    if explicit is not None:
        return explicit
    return _thickness_beside_grade(question, grade)


def _explicit_thickness(question: str) -> str | None:
    match = _EXPLICIT_THICKNESS_RE.search(question or "")
    if match is None:
        return None
    raw = next(group for group in match.groups() if group)
    return _thickness_text(raw)


def _thickness_beside_grade(question: str, grade: str) -> str | None:
    token = (grade or "").strip()
    if not token:
        return None
    escaped = re.escape(token)
    after = re.compile(
        escaped + r"\s*[,，、]?\s*(\d+\.\d+)",
        re.IGNORECASE,
    )
    before = re.compile(
        r"(\d+\.\d+)\s*[,，、的]?\s*" + escaped,
        re.IGNORECASE,
    )
    match = after.search(question or "") or before.search(question or "")
    if match is None:
        return None
    return _thickness_text(match.group(1))


def _thickness_text(raw: str) -> str | None:
    try:
        number = Decimal(raw)
    except InvalidOperation:
        return None
    if number <= 0 or number > _THICKNESS_MAX:
        return None
    quantized = number.quantize(Decimal("0.0001"))
    text = f"{quantized:.4f}".rstrip("0").rstrip(".")
    return text or None
