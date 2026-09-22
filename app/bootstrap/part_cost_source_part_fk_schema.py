"""存量库给零件核价补 source_part_id → stamping_parts RESTRICT（create_all 不改已有表）。"""

from __future__ import annotations

from typing import cast

from sqlalchemy import Engine, Table, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError

from app.bootstrap.sqlite_rebuild import (
    copy_shared_rows,
    drop_indexes,
    has_foreign_key,
    table_exists,
)
from app.utils.logging_config import get_logger

logger = get_logger("bootstrap.part_cost_source_part_fk_schema")

_TABLE = "stamping_part_costs"
_OLD = "stamping_part_costs__old_fk"
_PARENT = "stamping_parts"


def ensure_part_cost_source_part_fk_schema(engine: Engine) -> None:
    """source_part_id 挂零件 RESTRICT。对不上或为空则拒绝迁移，不删历史。"""
    from app.database import Base
    from app.models.costing.stamping_part_cost import StampingPartCost

    try:
        with engine.begin() as connection:
            if not table_exists(connection, _TABLE):
                return
            if has_foreign_key(connection, _TABLE, _PARENT, "source_part_id"):
                return
            orphan_count = _orphan_source_count(connection)
            if orphan_count:
                raise OperationalError(
                    "part cost source_part_id orphans",
                    {},
                    Exception(
                        f"{_TABLE} 有 {orphan_count} 行来源零件为空或不在 {_PARENT}，"
                        "拒绝重建外键，未改表、未删历史"
                    ),
                )
            logger.warning("重建 %s 以补 source_part_id RESTRICT", _TABLE)
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            connection.execute(text(f"ALTER TABLE {_TABLE} RENAME TO {_OLD}"))
            drop_indexes(connection, _OLD)
            connection.execute(text("PRAGMA foreign_keys=ON"))

        Base.metadata.create_all(
            bind=engine,
            tables=[cast(Table, StampingPartCost.__table__)],
        )

        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            copy_shared_rows(connection, _OLD, _TABLE)
            connection.execute(text(f"DROP TABLE IF EXISTS {_OLD}"))
            connection.execute(text("PRAGMA foreign_keys=ON"))
        logger.info("零件核价 source_part_id RESTRICT 已对齐")
    except OperationalError:
        logger.exception("无法补齐零件核价 source_part_id 外键")
        raise


def _orphan_source_count(connection: Connection) -> int:
    if not table_exists(connection, _PARENT):
        row = connection.execute(text(f"SELECT count(id) FROM {_TABLE}")).scalar()
        return int(row or 0)
    row = connection.execute(
        text(
            f"SELECT count(id) FROM {_TABLE} "
            f"WHERE source_part_id IS NULL "
            f"OR source_part_id NOT IN (SELECT id FROM {_PARENT})"
        )
    ).scalar()
    return int(row or 0)
