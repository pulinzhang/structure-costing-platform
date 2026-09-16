"""存量库补 LLM 报告列（create_all 不改已有表）。"""

from __future__ import annotations

from sqlalchemy import Engine, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError

from app.utils.logging_config import get_logger

logger = get_logger("bootstrap.llm_report_schema")

_TABLE = "llm_analysis_reports"
_COLUMNS: tuple[tuple[str, str], ...] = (("query_json", "TEXT"),)


def ensure_llm_report_schema(engine: Engine) -> None:
    try:
        with engine.begin() as connection:
            if not _table_exists(connection, _TABLE):
                return
            existing = _column_names(connection, _TABLE)
            for name, sql_type in _COLUMNS:
                if name in existing:
                    continue
                connection.execute(text(f"ALTER TABLE {_TABLE} ADD COLUMN {name} {sql_type}"))
                logger.info("已加列 %s.%s", _TABLE, name)
        logger.info("LLM 报告表结构已对齐")
    except OperationalError:
        logger.exception("无法补齐 LLM 报告表结构")
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
