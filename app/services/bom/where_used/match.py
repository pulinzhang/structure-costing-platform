"""零件用在哪：查询串分类。"""

from __future__ import annotations

import re
from typing import Literal

from app.common.part_number import (
    is_temporal_part_number_token,
    normalize_part_number_token,
)
from app.exceptions.base import BusinessException

MatchKind = Literal["short_code", "like_part", "internal_number"]

_FOUR_DIGIT = re.compile(r"^\d{4}$")
HIT_LIMIT = 2000
SHORT_CODE_CANDIDATE_LIMIT = 20000


def plan_match(*, raw_query: str, match: str) -> tuple[MatchKind, str, str]:
    """返回 (种类, 用于零件号的 token, 用于名称 LIKE 的原文)。"""
    raw = (raw_query or "").strip()
    if not raw:
        raise BusinessException("请输入零件号、4 位短码或名称")
    if match == "internal_number":
        return "internal_number", raw, raw
    if _FOUR_DIGIT.fullmatch(raw):
        if is_temporal_part_number_token(raw):
            raise BusinessException("不是零件短码")
        return "short_code", raw, raw
    if len(raw) < 2:
        raise BusinessException("请至少输入 2 个字或 4 位短码")
    return "like_part", normalize_part_number_token(raw), raw
