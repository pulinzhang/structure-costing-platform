"""工程变更三张表：全新切片，旧表直接 DROP 后按工程变更单实体重建。"""

from __future__ import annotations

from typing import cast

from sqlalchemy import Engine, Table, text
from sqlalchemy.engine import Connection

from app.utils.logging_config import get_logger

logger = get_logger("bootstrap.engineering_change_schema")

_TABLE_LINKS = "engineering_change_effect_links"
_TABLE_ORDERS = "engineering_change_orders"
_TABLE_COVERS_LEGACY = "engineering_change_covers"
_TABLE_LOGS = "engineering_change_upload_logs"


def ensure_engineering_change_schema(engine: Engine) -> None:
    """缺列 / 旧 cover 一律 DROP 三表再建；不迁数据、不调业务 Service。"""
    from app.database import Base
    from app.models.engineering_change.change_order import EngineeringChangeOrder
    from app.models.engineering_change.effect_link import EngineeringChangeEffectLink
    from app.models.engineering_change.upload_log import EngineeringChangeUploadLog

    with engine.begin() as connection:
        if not _needs_rebuild(connection):
            return
        logger.warning("工程变更历史表 DROP（清孤儿与无法挂 FK 的历史，不迁数据）")
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.execute(text(f"DROP TABLE IF EXISTS {_TABLE_LINKS}"))
        connection.execute(text(f"DROP TABLE IF EXISTS {_TABLE_COVERS_LEGACY}"))
        connection.execute(text(f"DROP TABLE IF EXISTS {_TABLE_ORDERS}"))
        connection.execute(text(f"DROP TABLE IF EXISTS {_TABLE_LOGS}"))
        connection.execute(text("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(
        bind=engine,
        tables=[
            cast(Table, EngineeringChangeUploadLog.__table__),
            cast(Table, EngineeringChangeOrder.__table__),
            cast(Table, EngineeringChangeEffectLink.__table__),
        ],
    )
    logger.info("工程变更三张表已重建")


def _needs_rebuild(connection: Connection) -> bool:
    if _table_exists(connection, _TABLE_COVERS_LEGACY):
        return True
    if not _table_exists(connection, _TABLE_ORDERS):
        return False
    order_cols = _column_names(connection, _TABLE_ORDERS)
    if "before_assembly_node_id" not in order_cols:
        return True
    if _table_exists(connection, _TABLE_LINKS):
        link_cols = _column_names(connection, _TABLE_LINKS)
        if "cover_id" in link_cols or "change_order_id" not in link_cols:
            return True
    return False


def _table_exists(connection: Connection, table_name: str) -> bool:
    row = connection.execute(
        text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name},
    ).first()
    return row is not None


def _column_names(connection: Connection, table_name: str) -> set[str]:
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).all()
    return {str(row[1]) for row in rows}
