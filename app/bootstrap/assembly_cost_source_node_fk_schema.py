"""存量库给总成核价补 source_node_id → bom_nodes RESTRICT（create_all 不改已有表）。"""

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

logger = get_logger("bootstrap.assembly_cost_source_node_fk_schema")

_TABLE_COSTS = "costing_assembly_costs"
_TABLE_ITEMS = "costing_assembly_cost_items"
_TABLE_INDIRECTS = "costing_assembly_cost_indirects"
_OLD_COSTS = "costing_assembly_costs__old_fk"
_OLD_ITEMS = "costing_assembly_cost_items__old_fk"
_OLD_INDIRECTS = "costing_assembly_cost_indirects__old_fk"
_PARENT_TABLE = "bom_nodes"


def ensure_assembly_cost_source_node_fk_schema(engine: Engine) -> None:
    """主表 source_node_id 挂节点 RESTRICT。对不上的行拒绝迁移，不删历史。"""
    from app.database import Base
    from app.models.costing.assembly_cost import AssemblyCost
    from app.models.costing.assembly_cost_indirect import AssemblyCostIndirect
    from app.models.costing.assembly_cost_item import AssemblyCostItem

    try:
        with engine.begin() as connection:
            if not table_exists(connection, _TABLE_COSTS):
                return
            if has_foreign_key(connection, _TABLE_COSTS, _PARENT_TABLE, "source_node_id"):
                return
            orphan_count = _orphan_source_count(connection)
            if orphan_count:
                raise OperationalError(
                    "assembly cost source_node_id orphans",
                    {},
                    Exception(
                        f"{_TABLE_COSTS} 有 {orphan_count} 行核价根不在 {_PARENT_TABLE}，"
                        "拒绝重建外键，未改表、未删历史"
                    ),
                )
            logger.warning("重建 %s 以补 source_node_id RESTRICT", _TABLE_COSTS)
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            connection.execute(text(f"ALTER TABLE {_TABLE_COSTS} RENAME TO {_OLD_COSTS}"))
            if table_exists(connection, _TABLE_ITEMS):
                connection.execute(text(f"ALTER TABLE {_TABLE_ITEMS} RENAME TO {_OLD_ITEMS}"))
            if table_exists(connection, _TABLE_INDIRECTS):
                connection.execute(
                    text(f"ALTER TABLE {_TABLE_INDIRECTS} RENAME TO {_OLD_INDIRECTS}")
                )
            drop_indexes(connection, _OLD_COSTS)
            if table_exists(connection, _OLD_ITEMS):
                drop_indexes(connection, _OLD_ITEMS)
            if table_exists(connection, _OLD_INDIRECTS):
                drop_indexes(connection, _OLD_INDIRECTS)
            connection.execute(text("PRAGMA foreign_keys=ON"))

        Base.metadata.create_all(
            bind=engine,
            tables=[
                cast(Table, AssemblyCost.__table__),
                cast(Table, AssemblyCostItem.__table__),
                cast(Table, AssemblyCostIndirect.__table__),
            ],
        )

        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            copy_shared_rows(connection, _OLD_COSTS, _TABLE_COSTS)
            child_where = f"assembly_cost_id IN (SELECT id FROM {_TABLE_COSTS})"
            if table_exists(connection, _OLD_ITEMS):
                copy_shared_rows(connection, _OLD_ITEMS, _TABLE_ITEMS, where=child_where)
            if table_exists(connection, _OLD_INDIRECTS):
                copy_shared_rows(connection, _OLD_INDIRECTS, _TABLE_INDIRECTS, where=child_where)
            connection.execute(text(f"DROP TABLE IF EXISTS {_OLD_INDIRECTS}"))
            connection.execute(text(f"DROP TABLE IF EXISTS {_OLD_ITEMS}"))
            connection.execute(text(f"DROP TABLE IF EXISTS {_OLD_COSTS}"))
            connection.execute(text("PRAGMA foreign_keys=ON"))
        logger.info("总成核价 source_node_id RESTRICT 已对齐")
    except OperationalError:
        logger.exception("无法补齐总成核价 source_node_id 外键")
        raise


def _orphan_source_count(connection: Connection) -> int:
    if not table_exists(connection, _PARENT_TABLE):
        row = connection.execute(text(f"SELECT count(id) FROM {_TABLE_COSTS}")).scalar()
        return int(row or 0)
    row = connection.execute(
        text(
            f"SELECT count(id) FROM {_TABLE_COSTS} "
            f"WHERE source_node_id NOT IN (SELECT id FROM {_PARENT_TABLE})"
        )
    ).scalar()
    return int(row or 0)
