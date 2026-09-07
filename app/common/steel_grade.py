"""钢材牌号比对：Excel 常见把数字 0 写成字母 O。"""

from __future__ import annotations


def grade_match_key(raw: str | None) -> str:
    """去空格、大写；字母 O 与数字 0 视为同一字符（DCO3 ≡ DC03）。"""
    return (raw or "").strip().upper().replace("O", "0")
