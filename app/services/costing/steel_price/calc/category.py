"""钢材联动：牌号用来查出冷轧/镀锌/酸洗，供厚度大类政策使用。"""

from __future__ import annotations

from collections.abc import Mapping

from app.common.steel_grade_category import as_canonical_category
from app.schemas.vo.steel_grade_category_vo import SteelGradeCategoryVO


def resolve_canonical_category(
    grade: str,
    category_map: Mapping[str, SteelGradeCategoryVO],
) -> str:
    """工艺牌号或已是大类名 → 规范三字；档案没有该牌号 → 空串。"""
    direct = as_canonical_category(grade)
    if direct:
        return direct
    archive = category_map.get((grade or "").strip())
    if archive is None:
        return ""
    return as_canonical_category(archive.category_name) or ""
