"""基准价环比问句里，操作员点名的相差金额。"""

from __future__ import annotations

import re

from app.services.llm.query.parser.subjects import is_base_price_question

_AMOUNT_RE = re.compile(r"(?:相差|超过|大于|高出|超)\s*±?\s*(\d+(?:\.\d+)?)")
_MOVE_WORDS = ("环比", "相差", "涨跌", "超过", "超")


def month_move_over_amount(question: str) -> str | None:
    """问句里的相差金额。没有写数字则不按这条回答。"""
    text = question or ""
    if not is_base_price_question(text):
        return None
    if not any(word in text for word in _MOVE_WORDS):
        return None
    match = _AMOUNT_RE.search(text)
    if match is None:
        return None
    return match.group(1)
