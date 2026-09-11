"""钢材牌号：落库去空格并大写；匹配键把字母 O 改成 0 再大写。

查档案请用 `SteelGradeCategoryService.match_by_grade_key`。
只比两个字符串（如核价基价行）可直接用 `grade_match_key`。
"""

from __future__ import annotations


def stored_grade(raw: str | None) -> str:
    """档案落库：去前后空格、全部大写。不改字母 O / 数字 0。"""
    return (raw or "").strip().upper()


def grade_match_key(raw: str | None) -> str:
    """匹配键：去空格，字母 O/o → 0，再全大写。只用于比较，不用于落库。"""
    return (raw or "").strip().replace("O", "0").replace("o", "0").upper()
