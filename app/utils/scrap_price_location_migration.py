"""
废料销售价表：base_name → location 列重命名迁移。

旧表含 base_name 时直接 DROP，由后续 create_tables 按最新 Model 重建。
该表为新功能，无生产数据依赖。
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.utils.logging_config import get_logger


logger = get_logger("scrap_price_location_migration")

TABLE_NAME = "stamping_scrap_prices"


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:name"
        ),
        {"name": table_name},
    ).fetchone()
    return row is not None


def _column_names(conn, table_name: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {row[1] for row in rows}


def run_scrap_price_location_migration(engine: Engine) -> None:
    """若仍为 base_name 旧结构则 DROP，交由 create_tables 重建。"""
    if engine.dialect.name != "sqlite":
        logger.info("[scrap_price_migration] 非 SQLite，跳过")
        return

    with engine.begin() as conn:
        if not _table_exists(conn, TABLE_NAME):
            logger.info("[scrap_price_migration] 表不存在，跳过")
            return

        columns = _column_names(conn, TABLE_NAME)
        if "base_name" not in columns:
            logger.info("[scrap_price_migration] 已是 location 结构，跳过")
            return

        conn.execute(text(f"DROP TABLE {TABLE_NAME}"))
        logger.warning(
            "[scrap_price_migration] 检测到 base_name 旧列，已 DROP %s，"
            "将由 create_tables 重建为 location",
            TABLE_NAME,
        )
