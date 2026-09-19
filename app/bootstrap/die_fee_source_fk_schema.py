"""存量库给模具费结果补 source_die_part_id → 布点 RESTRICT（create_all 不改已有表）。"""

from __future__ import annotations

from typing import cast

from sqlalchemy import Engine, Table, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError

from app.utils.logging_config import get_logger

logger = get_logger("bootstrap.die_fee_source_fk_schema")

_TABLE_FEES = "stamping_die_fees"
_TABLE_ITEMS = "stamping_die_fee_items"
_OLD_FEES = "stamping_die_fees__old_fk"
_OLD_ITEMS = "stamping_die_fee_items__old_fk"


def ensure_die_fee_source_fk_schema(engine: Engine) -> None:
    """对齐加工费：主表 source_die_part_id 挂布点 RESTRICT；工序指针仍软引用。"""
    from app.database import Base
    from app.models.stamping.die_fee import StampingDieFee
    from app.models.stamping.die_fee_item import StampingDieFeeItem

    try:
        with engine.begin() as connection:
            if not _table_exists(connection, _TABLE_FEES):
                return
            if _has_source_die_part_fk(connection):
                return
            logger.warning("重建 %s 以补 source_die_part_id RESTRICT", _TABLE_FEES)
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            connection.execute(text(f"ALTER TABLE {_TABLE_FEES} RENAME TO {_OLD_FEES}"))
            if _table_exists(connection, _TABLE_ITEMS):
                connection.execute(text(f"ALTER TABLE {_TABLE_ITEMS} RENAME TO {_OLD_ITEMS}"))
            # SQLite 表改名后索引名仍占用全局命名空间，create_all 会撞名
            _drop_indexes_for_table(connection, _OLD_FEES)
            if _table_exists(connection, _OLD_ITEMS):
                _drop_indexes_for_table(connection, _OLD_ITEMS)
            connection.execute(text("PRAGMA foreign_keys=ON"))

        Base.metadata.create_all(
            bind=engine,
            tables=[
                cast(Table, StampingDieFee.__table__),
                cast(Table, StampingDieFeeItem.__table__),
            ],
        )

        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            _copy_fees(connection)
            if _table_exists(connection, _OLD_ITEMS):
                _copy_items(connection)
            connection.execute(text(f"DROP TABLE IF EXISTS {_OLD_ITEMS}"))
            connection.execute(text(f"DROP TABLE IF EXISTS {_OLD_FEES}"))
            connection.execute(text("PRAGMA foreign_keys=ON"))
        logger.info("模具费 source_die_part_id RESTRICT 已对齐")
    except OperationalError:
        logger.exception("无法补齐模具费 source_die_part_id 外键")
        raise


def _drop_indexes_for_table(connection: Connection, table_name: str) -> None:
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


def _has_source_die_part_fk(connection: Connection) -> bool:
    rows = connection.execute(text(f"PRAGMA foreign_key_list({_TABLE_FEES})")).all()
    for row in rows:
        referred = str(row[2])
        from_col = str(row[3])
        if referred == "stamping_die_parts" and from_col == "source_die_part_id":
            return True
    return False


def _copy_fees(connection: Connection) -> None:
    old_cols = _column_names(connection, _OLD_FEES)
    new_cols = _column_names(connection, _TABLE_FEES)
    shared = [name for name in new_cols if name in old_cols]
    if not shared:
        return
    columns = ", ".join(shared)
    connection.execute(
        text(
            f"""
            INSERT INTO {_TABLE_FEES} ({columns})
            SELECT {columns}
            FROM {_OLD_FEES}
            WHERE source_die_part_id IS NULL
               OR source_die_part_id IN (SELECT id FROM stamping_die_parts)
            """
        )
    )


def _copy_items(connection: Connection) -> None:
    old_cols = _column_names(connection, _OLD_ITEMS)
    new_cols = _column_names(connection, _TABLE_ITEMS)
    shared = [name for name in new_cols if name in old_cols]
    if not shared:
        return
    columns = ", ".join(shared)
    connection.execute(
        text(
            f"""
            INSERT INTO {_TABLE_ITEMS} ({columns})
            SELECT {columns}
            FROM {_OLD_ITEMS}
            WHERE fee_id IN (SELECT id FROM {_TABLE_FEES})
            """
        )
    )


def _table_exists(connection: Connection, table_name: str) -> bool:
    row = connection.execute(
        text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name},
    ).first()
    return row is not None


def _column_names(connection: Connection, table_name: str) -> set[str]:
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).all()
    return {str(row[1]) for row in rows}
