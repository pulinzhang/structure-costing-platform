"""存量库给模具费结果补 source_die_part_id → 布点 RESTRICT（create_all 不改已有表）。"""

from __future__ import annotations

from typing import cast

from sqlalchemy import Engine, Table, text
from sqlalchemy.exc import OperationalError

from app.bootstrap.sqlite_rebuild import (
    copy_shared_rows,
    drop_indexes,
    has_foreign_key,
    table_exists,
)
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
            if not table_exists(connection, _TABLE_FEES):
                return
            if has_foreign_key(connection, _TABLE_FEES, "stamping_die_parts", "source_die_part_id"):
                return
            logger.warning("重建 %s 以补 source_die_part_id RESTRICT", _TABLE_FEES)
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            connection.execute(text(f"ALTER TABLE {_TABLE_FEES} RENAME TO {_OLD_FEES}"))
            if table_exists(connection, _TABLE_ITEMS):
                connection.execute(text(f"ALTER TABLE {_TABLE_ITEMS} RENAME TO {_OLD_ITEMS}"))
            drop_indexes(connection, _OLD_FEES)
            if table_exists(connection, _OLD_ITEMS):
                drop_indexes(connection, _OLD_ITEMS)
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
            copy_shared_rows(
                connection,
                _OLD_FEES,
                _TABLE_FEES,
                where=(
                    "source_die_part_id IS NULL "
                    "OR source_die_part_id IN (SELECT id FROM stamping_die_parts)"
                ),
            )
            if table_exists(connection, _OLD_ITEMS):
                copy_shared_rows(
                    connection,
                    _OLD_ITEMS,
                    _TABLE_ITEMS,
                    where=f"fee_id IN (SELECT id FROM {_TABLE_FEES})",
                )
            connection.execute(text(f"DROP TABLE IF EXISTS {_OLD_ITEMS}"))
            connection.execute(text(f"DROP TABLE IF EXISTS {_OLD_FEES}"))
            connection.execute(text("PRAGMA foreign_keys=ON"))
        logger.info("模具费 source_die_part_id RESTRICT 已对齐")
    except OperationalError:
        logger.exception("无法补齐模具费 source_die_part_id 外键")
        raise
