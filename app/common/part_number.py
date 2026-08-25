"""零件号口语片段与全码的模糊匹配（行业常用 4 位简码）。"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TypeVar

_PART_FULL_RE = re.compile(
    r"(?<![A-Za-z0-9])([A-Z0-9]{8,}[A-Za-z0-9\-]*)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
# 4 位数字简码；排除 19xx/20xx 年份及「2026年」类写法
_PART_SHORT_RE = re.compile(
    r"(?<![0-9])(?!(?:19|20)\d{2})(\d{4})(?!\d|年)",
)

_YEAR_TOKEN_RE = re.compile(r"^(?:19|20)\d{2}$")
_YM_HYPHEN_RE = re.compile(r"^(?:19|20)\d{2}-(?:0[1-9]|1[0-2])$")
_YM_COMPACT_RE = re.compile(r"^(?:19|20)\d{2}(?:0[1-9]|1[0-2])$")
_YMD_COMPACT_RE = re.compile(r"^(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])$")

T = TypeVar("T")


def escape_like_fragment(value: str) -> str:
    return (value or "").strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def part_number_like_pattern(fragment: str) -> str:
    token = escape_like_fragment(fragment)
    return f"%{token}%" if token else "%"


def normalize_part_number_token(value: str) -> str:
    return (value or "").strip().upper()


def is_temporal_part_number_token(value: str) -> bool:
    """年份 / 年月 / 年月日写法，不是零件号。"""
    token = normalize_part_number_token(value)
    if not token:
        return False
    if _YEAR_TOKEN_RE.fullmatch(token):
        return True
    if _YM_HYPHEN_RE.fullmatch(token):
        return True
    if _YM_COMPACT_RE.fullmatch(token):
        return True
    return bool(_YMD_COMPACT_RE.fullmatch(token))


def sanitize_part_number_token(value: str) -> str | None:
    """剔除时间 token；合法零件号片段则返回规范化大写串。"""
    token = normalize_part_number_token(value)
    if not token or is_temporal_part_number_token(token):
        return None
    return token


def part_numbers_match(row_part_number: str, query_token: str) -> bool:
    row = normalize_part_number_token(row_part_number)
    token = sanitize_part_number_token(query_token)
    if not row or not token:
        return False
    if row == token:
        return True
    return token in row


def extract_part_number_from_text(text: str) -> str | None:
    """从问句抽取全码或 4 位数字简码（排除年份/年月）。"""
    question = (text or "").strip()
    if not question:
        return None
    full = _PART_FULL_RE.search(question)
    if full:
        return sanitize_part_number_token(full.group(1))
    short = _PART_SHORT_RE.search(question)
    if short:
        return sanitize_part_number_token(short.group(1))
    return None


def pick_part_row(
    rows: list[T],
    query_token: str,
    *,
    get_part_number: Callable[[T], str],
) -> T | None:
    token = sanitize_part_number_token(query_token)
    if not rows or not token:
        return None
    exact = next(
        (row for row in rows if normalize_part_number_token(get_part_number(row)) == token),
        None,
    )
    if exact is not None:
        return exact
    matched = [row for row in rows if part_numbers_match(get_part_number(row), token)]
    return matched[0] if matched else None
