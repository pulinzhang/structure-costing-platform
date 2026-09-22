"""SQLite 不能 ALTER 外键时，改名重建用的公共步骤。各表自己的取舍留在对应 schema 文件。"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.utils.logging_config import get_logger

logger = get_logger("bootstrap.sqlite_rebuild")


def table_exists(connection: Connection, table_name: str) -> bool:
    row = connection.execute(
        text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name},
    ).first()
    return row is not None


def column_names(connection: Connection, table_name: str) -> set[str]:
    """PRAGMA table_info 第 2 列是列名。"""
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).all()
    return {str(row[1]) for row in rows}


def drop_indexes(connection: Connection, table_name: str) -> None:
    """表改名后索引名仍占全局。create_all 前必须删掉，否则同名索引建不出来。"""
    rows = connection.execute(
        text(
            "SELECT name FROM sqlite_master "
            "WHERE type='index' AND tbl_name=:table_name AND name IS NOT NULL"
        ),
        {"table_name": table_name},
    ).all()
    for (name,) in rows:
        index_name = str(name)
        if index_name.startswith("sqlite_autoindex_"):
            continue
        connection.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))
        logger.info("已删旧索引 %s（表 %s）", index_name, table_name)


def has_foreign_key(connection: Connection, table_name: str, referred: str, column: str) -> bool:
    """PRAGMA foreign_key_list：第 3 列是被引用表，第 4 列是本表列。"""
    rows = connection.execute(text(f"PRAGMA foreign_key_list({table_name})")).all()
    return any(str(row[2]) == referred and str(row[3]) == column for row in rows)


def copy_shared_rows(
    connection: Connection,
    old_table: str,
    new_table: str,
    *,
    where: str = "",
) -> None:
    """按两边都有的列拷行。where 由调用方写，用来决定丢不丢对不上的历史。"""
    old_cols = column_names(connection, old_table)
    new_cols = column_names(connection, new_table)
    shared = [name for name in new_cols if name in old_cols]
    if not shared:
        return
    columns = ", ".join(shared)
    suffix = f" WHERE {where}" if where else ""
    connection.execute(
        text(f"INSERT INTO {new_table} ({columns}) SELECT {columns} FROM {old_table}{suffix}")
    )
