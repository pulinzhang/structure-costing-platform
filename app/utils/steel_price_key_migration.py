"""
钢材价格表结构迁移工具

旧表（导入价目 / 旧业务主键）无法通过 ADD COLUMN 平滑升级到
「计算结果 + 溯源 + 审核」新结构。检测到旧结构时直接 DROP，
由后续 create_tables 按最新 Model 重建空表。
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.utils.logging_config import get_logger


logger = get_logger("steel_price_schema_migration")

TABLE_NAME = "steel_prices"

# 新表必备列；缺少任一列即视为旧结构
NEW_SCHEMA_REQUIRED_COLUMNS = {
    "location",
    "category_name",
    "width",
    "base_price",
    "width_adjustment",
    "zinc_adjustment",
    "other_adjustment",
    "calc_batch_id",
    "match_status",
    "calc_status",
    "formula_version",
    "calculated_at",
    "audit_status",
    "reverse_audited_by",
    "reverse_audited_at",
    "reverse_audit_remark",
}

# 旧表特征列（存在则确认是旧结构）
LEGACY_MARKER_COLUMNS = {"bid_price", "steel_type", "reference_spec"}


def _table_exists(conn, table_name: str) -> bool:
    row = conn.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:name"
        ),
        {"name": table_name},
    ).fetchone()
    return row is not None


def _table_columns(conn, table_name: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return {row[1] for row in rows}


def run_steel_price_key_migration(engine: Engine) -> None:
    """检测并重建钢材价格表（仅 SQLite）。"""
    if engine.dialect.name != "sqlite":
        return

    with engine.connect() as conn:
        if not _table_exists(conn, TABLE_NAME):
            return

        columns = _table_columns(conn, TABLE_NAME)
        has_new_schema = NEW_SCHEMA_REQUIRED_COLUMNS.issubset(columns)
        has_legacy_marker = bool(columns & LEGACY_MARKER_COLUMNS)

        if has_new_schema and not has_legacy_marker:
            return

        logger.warning(
            "检测到 steel_prices 旧结构（columns=%s），将 DROP 后由 create_tables 重建",
            sorted(columns),
        )
        conn.execute(text(f"DROP TABLE IF EXISTS {TABLE_NAME}"))
        conn.commit()
        logger.info("steel_prices 旧表已删除，等待 create_tables 按新 Model 重建")
