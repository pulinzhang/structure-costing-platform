"""存量库给焊接费补 source_breakdown_node_id → 拆解 RESTRICT（create_all 不改已有表）。"""

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

logger = get_logger("bootstrap.welding_fee_source_fk_schema")

_TABLE_FEES = "bom_welding_fees"
_TABLE_ITEMS = "bom_welding_fee_items"
_OLD_FEES = "bom_welding_fees__old_fk"
_OLD_ITEMS = "bom_welding_fee_items__old_fk"
_PARENT_TABLE = "bom_welding_process_breakdown_node"


def ensure_welding_fee_source_fk_schema(engine: Engine) -> None:
    """主表 source_breakdown_node_id 挂拆解 RESTRICT；明细仍 CASCADE 到费行。"""
    from app.database import Base
    from app.models.bom.welding_fee import BomWeldingFee
    from app.models.bom.welding_fee_item import BomWeldingFeeItem

    try:
        with engine.begin() as connection:
            if not table_exists(connection, _TABLE_FEES):
                return
            if has_foreign_key(connection, _TABLE_FEES, _PARENT_TABLE, "source_breakdown_node_id"):
                return
            logger.warning("重建 %s 以补 source_breakdown_node_id RESTRICT", _TABLE_FEES)
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
                cast(Table, BomWeldingFee.__table__),
                cast(Table, BomWeldingFeeItem.__table__),
            ],
        )

        with engine.begin() as connection:
            connection.execute(text("PRAGMA foreign_keys=OFF"))
            if table_exists(connection, _PARENT_TABLE):
                fee_where = (
                    "source_breakdown_node_id IS NULL "
                    f"OR source_breakdown_node_id IN (SELECT id FROM {_PARENT_TABLE})"
                )
            else:
                fee_where = "source_breakdown_node_id IS NULL"
            copy_shared_rows(connection, _OLD_FEES, _TABLE_FEES, where=fee_where)
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
        logger.info("焊接费 source_breakdown_node_id RESTRICT 已对齐")
    except OperationalError:
        logger.exception("无法补齐焊接费 source_breakdown_node_id 外键")
        raise
