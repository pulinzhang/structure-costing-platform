"""删除前按当前连接发现外键并计数。有引用则抛短句，明细放在 audit_detail。"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.repositories.settings.schema_comment.repository import (
    ForeignKeyRef,
    SchemaCommentRepository,
    is_blocking,
    is_plain_identifier,
)

logger = logging.getLogger("service.settings.schema_comment")

STILL_REFERENCED = "仍被引用，不能删除"


def ensure_deletable(
    db: Session,
    parent_table: str,
    key_rows: Sequence[Mapping[str, object]],
    subject: str | None = None,
) -> None:
    """有挡住删除的引用则抛 BusinessException。不 commit，不开新连接。"""
    if not key_rows:
        return
    if not is_plain_identifier(parent_table):
        raise ValueError(f"非法父表名: {parent_table}")
    repository = SchemaCommentRepository()
    if parent_table not in repository.list_table_names(db):
        logger.warning("删除检查未找到父表 %s，放行", parent_table)
        return
    groups = [
        ref
        for ref in repository.list_foreign_keys(db)
        if ref.parent_table == parent_table and is_blocking(ref.on_delete)
    ]
    groups.sort(key=lambda ref: (ref.child_table, ref.constraint_id))
    hits: list[tuple[ForeignKeyRef, int]] = []
    for ref in groups:
        values = _key_values(ref, key_rows)
        count = repository.count_matches(
            db,
            child_table=ref.child_table,
            child_columns=ref.child_columns,
            key_rows=values,
        )
        if count > 0:
            hits.append((ref, count))
    if not hits:
        return
    names = repository.load_names(db, [ref.child_table for ref, _count in hits])
    hints = repository.load_hints(db, parent_table)
    detail = _detail(subject or "该记录", hits, names, hints)
    raise BusinessException(STILL_REFERENCED, audit_detail=detail)


def _key_values(
    ref: ForeignKeyRef,
    key_rows: Sequence[Mapping[str, object]],
) -> list[tuple[object, ...]]:
    rows: list[tuple[object, ...]] = []
    for key_row in key_rows:
        values: list[object] = []
        for column in ref.parent_columns:
            if column not in key_row:
                raise ValueError(f"缺少父列 {column}")
            values.append(key_row[column])
        rows.append(tuple(values))
    return rows


def _detail(
    subject: str,
    hits: list[tuple[ForeignKeyRef, int]],
    names: dict[str, str],
    hints: dict[str, str],
) -> str:
    lines = [f"无法删除{subject}，原因如下："]
    for ref, count in hits:
        lines.append(f"  - {_bullet(ref.child_table, count, names, hints)}")
    lines.append("请处理完以上数据后再删除。")
    return "\n".join(lines)


def _bullet(child_table: str, count: int, names: dict[str, str], hints: dict[str, str]) -> str:
    name_zh = names.get(child_table)
    hint = hints.get(child_table)
    if name_zh and hint:
        return f"有 {count} 条{name_zh}，{hint}"
    if name_zh:
        return f"有 {count} 条{name_zh}，请先处理{name_zh}"
    return f"被 {child_table} 表引用 {count} 条，请联系管理员处理"
