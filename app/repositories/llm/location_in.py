"""LLM 切片内按主数据展开基地名；禁止调上游 LocationService。"""

from __future__ import annotations

from sqlalchemy import false
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.sql.elements import ColumnElement

from app.repositories.llm.scope_options_repository import ScopeOptionsRepository

_scope_repo = ScopeOptionsRepository()


def location_in_clause(
    db: Session,
    column: InstrumentedAttribute[str],
    location: str | None,
) -> ColumnElement[bool] | None:
    text = (location or "").strip()
    if not text:
        return None
    names = _scope_repo.expand_location_names(db, text)
    if not names:
        return false()
    return column.in_(names)


def location_in_or_exact_clause(
    db: Session,
    column: InstrumentedAttribute[str],
    location: str | None,
) -> ColumnElement[bool] | None:
    """主数据能展开则 IN；否则精确匹配。"""
    text = (location or "").strip()
    if not text:
        return None
    names = _scope_repo.expand_location_names(db, text)
    if names:
        return column.in_(names)
    return column == text


def expand_location_list(db: Session, raw_names: list[str]) -> list[str]:
    seen: set[str] = set()
    names: list[str] = []
    for raw in raw_names:
        for item in _scope_repo.expand_location_names(db, raw):
            if item not in seen:
                seen.add(item)
                names.append(item)
    return names


def location_in_list_clause(
    db: Session,
    column: InstrumentedAttribute[str],
    raw_names: list[str],
) -> ColumnElement[bool]:
    names = expand_location_list(db, raw_names)
    if not names:
        return false()
    return column.in_(names)
