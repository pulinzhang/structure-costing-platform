"""政策列表/导出筛选：档案大类 → 政策表 category_name 别名；牌号 → 档案大类。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.common.steel_grade_category import normalize_category_name
from app.repositories.yishiyiyi.steel_grade_category.steel_grade_category_repository import (
    SteelGradeCategoryRepository,
)
from app.services.yishiyiyi.policy.match.adjustment_common import category_aliases


@dataclass(frozen=True, slots=True)
class ResolvedPolicyCategoryFilter:
    """解析后用于 policy.category_name IN (...) 的集合。"""

    policy_category_names: frozenset[str] | None = None
    no_match: bool = False


def _aliases_for_category(category_name: str) -> frozenset[str]:
    normalized = normalize_category_name(category_name) or category_name
    return category_aliases(normalized)


def _categories_for_grade(db: Session, grade_value: str) -> frozenset[str] | None:
    repo = SteelGradeCategoryRepository()
    exact = repo.get_by_grade(db, grade_value)
    if exact is not None and exact.category_name:
        return _aliases_for_category(exact.category_name)
    return None


def resolve_policy_category_filter(
    db: Session,
    *,
    category_name: str | None = None,
    grade_value: str | None = None,
) -> ResolvedPolicyCategoryFilter:
    """
    将筛选条件解析为政策表 category_name 可匹配的别名集合。

    - category_name：档案 canonical 大类（冷轧/镀锌/酸洗）→ 展开 IN 集合
    - grade_value：先查牌号分类档案得到大类，再展开；与 category_name 同时存在时取交集
    """
    alias_sets: list[frozenset[str]] = []

    cat = (category_name or "").strip()
    if cat:
        alias_sets.append(_aliases_for_category(cat))

    grade = (grade_value or "").strip()
    if grade:
        grade_aliases = _categories_for_grade(db, grade)
        if grade_aliases is None:
            return ResolvedPolicyCategoryFilter(no_match=True)
        alias_sets.append(grade_aliases)

    if not alias_sets:
        return ResolvedPolicyCategoryFilter()

    result = alias_sets[0]
    for alias_set in alias_sets[1:]:
        result = result & alias_set
    if not result:
        return ResolvedPolicyCategoryFilter(no_match=True)
    return ResolvedPolicyCategoryFilter(policy_category_names=result)
