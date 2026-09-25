"""按 logical_ref 头和 logical_ref_filter 条件计数。不发现外键，不读外键配置。"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.models.settings.logical_ref.model import LogicalRef
from app.repositories.settings.logical_ref.repository import LogicalRefRepository
from app.repositories.settings.logical_ref.sql import is_plain_identifier

logger = logging.getLogger("service.settings.logical_ref")


def ensure_logical_deletable(
    db: Session,
    deleted_table: str,
    key_rows: Sequence[Mapping[str, object]],
    subject: str | None = None,
) -> None:
    """只按条件行拼查询并计数。不发现外键。有挡住删除的结果则抛 BusinessException。不 commit，不开新连接。"""
    if not key_rows:
        return
    if not is_plain_identifier(deleted_table):
        raise ValueError(f"非法表名: {deleted_table}")
    repository = LogicalRefRepository()
    if deleted_table not in repository.list_table_names(db):
        logger.warning("逻辑引用检查未找到正在删除的表 %s，放行", deleted_table)
        return
    heads = repository.list_heads(db, deleted_table)
    if not heads:
        return
    key_columns = tuple(key_rows[0].keys())
    for column in key_columns:
        if not is_plain_identifier(column):
            raise ValueError(f"非法列名: {column}")
    values = [tuple(row[column] for column in key_columns) for row in key_rows]
    hits = [(head, repository.count(db, head, key_columns, values)) for head in heads]
    hits = [(head, count) for head, count in hits if count > 0]
    if not hits:
        return
    raise BusinessException(_detail(subject or "该记录", hits))


def _detail(subject: str, hits: list[tuple[LogicalRef, int]]) -> str:
    lines = [f"无法删除{subject}，原因如下："]
    for head, count in hits:
        lines.append(f"  - 有 {count} 条{head.result_name}，{head.hint}")
    lines.append("请处理完以上数据后再删除。")
    return "\n".join(lines)
