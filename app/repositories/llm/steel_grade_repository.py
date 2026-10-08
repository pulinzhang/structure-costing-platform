"""牌号分类档案 — LLM 只读确认问句里的牌号，不经主数据 Service。"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.masterdata.steel_grade_category import SteelGradeCategory


class SteelGradeRepository:
    def match_grade(self, db: Session, candidates: list[str]) -> str | None:
        """按问句出现顺序，返回档案里的牌号写法。对不上则 None。"""
        wanted: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            token = (candidate or "").strip()
            if not token:
                continue
            key = token.upper()
            if key in seen:
                continue
            seen.add(key)
            wanted.append(token)
        if not wanted:
            return None

        found = _index_grades(
            db.query(SteelGradeCategory.grade)
            .filter(func.upper(SteelGradeCategory.grade).in_([item.upper() for item in wanted]))
            .all()
        )
        for token in wanted:
            hit = found.get(token.upper())
            if hit:
                return hit
        return None


def _index_grades(rows: object) -> dict[str, str]:
    """查询结果不是列表时按未命中处理，避免假会话被当成档案行。"""
    if not isinstance(rows, list):
        return {}
    found: dict[str, str] = {}
    for row in rows:
        grade = str(row[0]).strip() if row and row[0] else ""
        if grade:
            found[grade.upper()] = grade
    return found
