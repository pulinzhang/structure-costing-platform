"""存量库补系统设置三列（create_all 不改已有表）。"""

from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError

from app.utils.logging_config import get_logger

logger = get_logger("bootstrap.system_config_schema")

_TABLE = "system_configs"
_COLUMNS: tuple[tuple[str, str], ...] = (
    (
        "base_price_month_move_limit",
        "NUMERIC(12, 2) NOT NULL DEFAULT 300",
    ),
    (
        "base_price_processing_fee_limit",
        "NUMERIC(12, 2) NOT NULL DEFAULT 120",
    ),
    (
        "body_panel_max_thickness",
        "NUMERIC(7, 2) NOT NULL DEFAULT 3.00",
    ),
)


def ensure_system_config_schema(engine: Engine) -> None:
    """缺列才加。默认：月度涨跌 ±300 元/吨，加工费上限 120 元/吨，料厚上限 3.00 mm。"""
    try:
        with engine.begin() as connection:
            if not _table_exists(connection, _TABLE):
                return
            existing = _column_names(connection, _TABLE)
            for name, definition in _COLUMNS:
                if name in existing:
                    continue
                connection.execute(text(f"ALTER TABLE {_TABLE} ADD COLUMN {name} {definition}"))
                logger.info("已加列 %s.%s", _TABLE, name)
        logger.info("系统设置表结构已对齐")
    except OperationalError:
        logger.exception("无法补齐系统设置表列")
        raise


def _table_exists(connection: Connection, table_name: str) -> bool:
    row = connection.execute(
        text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
        {"name": table_name},
    ).first()
    return row is not None


def _column_names(connection: Connection, table_name: str) -> set[str]:
    rows = connection.execute(text(f"PRAGMA table_info({table_name})")).all()
    return {str(row[1]) for row in rows}
