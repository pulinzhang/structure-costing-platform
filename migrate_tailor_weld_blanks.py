"""
一次性 SQLite 迁移：拼焊主表标识列 + 子片表

- ALTER ``stamping_parts``：追加 ``is_tailor_welded``（默认 0 / 否）
- CREATE ``stamping_tailor_weld_blanks``（若不存在则按 ORM 建表）
- ALTER 子表：追加冗余 ``parent_part_number``（若表已存在但缺列）

用法（仓库根目录）::

    python -X utf8 migrate_tailor_weld_blanks.py

幂等：列/表已存在则跳过对应步骤。仅支持主业务库 SQLite。
"""

from __future__ import annotations

import sys

from sqlalchemy import inspect, text

# 确保 ORM 表已注册到 Base.metadata
import app.models  # noqa: F401
from app.database import DatabaseConfig
from app.models.stamping import StampingTailorWeldBlank


COLUMN_NAME = "is_tailor_welded"
PARTS_TABLE = "stamping_parts"
INDEX_NAME = "ix_part_is_tailor_welded"
BLANKS_TABLE = "stamping_tailor_weld_blanks"
PARENT_PART_NUMBER_COLUMN = "parent_part_number"
PARENT_PART_NUMBER_INDEX = "ix_tailor_weld_blank_parent_part_number"


def _ensure_is_tailor_welded_column(engine) -> str:
    inspector = inspect(engine)
    if PARTS_TABLE not in inspector.get_table_names():
        return f"跳过 ALTER：表 {PARTS_TABLE} 不存在（可先启动应用 create_all）"

    existing = {col["name"] for col in inspector.get_columns(PARTS_TABLE)}
    if COLUMN_NAME in existing:
        return f"跳过 ALTER：{PARTS_TABLE}.{COLUMN_NAME} 已存在"

    # SQLite：BOOLEAN 存为 INTEGER；DEFAULT 0 覆盖已有行
    with engine.begin() as conn:
        conn.execute(
            text(
                f"ALTER TABLE {PARTS_TABLE} "
                f"ADD COLUMN {COLUMN_NAME} BOOLEAN NOT NULL DEFAULT 0"
            )
        )
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} "
                f"ON {PARTS_TABLE} ({COLUMN_NAME})"
            )
        )
    return f"已 ALTER：{PARTS_TABLE} 追加列 {COLUMN_NAME}，并创建索引 {INDEX_NAME}"


def _ensure_tailor_weld_blanks_table(engine) -> str:
    inspector = inspect(engine)
    table_name = StampingTailorWeldBlank.__tablename__
    if table_name in inspector.get_table_names():
        return f"跳过 CREATE：表 {table_name} 已存在"

    StampingTailorWeldBlank.__table__.create(bind=engine, checkfirst=True)
    return f"已 CREATE：表 {table_name}"


def _ensure_parent_part_number_column(engine) -> str:
    """已有子表缺冗余父零件号时补列，并从父表回填。"""
    inspector = inspect(engine)
    if BLANKS_TABLE not in inspector.get_table_names():
        return f"跳过 ALTER：表 {BLANKS_TABLE} 不存在"

    existing = {col["name"] for col in inspector.get_columns(BLANKS_TABLE)}
    if PARENT_PART_NUMBER_COLUMN in existing:
        return f"跳过 ALTER：{BLANKS_TABLE}.{PARENT_PART_NUMBER_COLUMN} 已存在"

    with engine.begin() as conn:
        conn.execute(
            text(
                f"ALTER TABLE {BLANKS_TABLE} "
                f"ADD COLUMN {PARENT_PART_NUMBER_COLUMN} VARCHAR(50) NOT NULL DEFAULT ''"
            )
        )
        conn.execute(
            text(
                f"UPDATE {BLANKS_TABLE} "
                f"SET {PARENT_PART_NUMBER_COLUMN} = ("
                f"  SELECT part_number FROM {PARTS_TABLE} "
                f"  WHERE {PARTS_TABLE}.id = {BLANKS_TABLE}.part_id"
                f") "
                f"WHERE {PARENT_PART_NUMBER_COLUMN} = ''"
            )
        )
        conn.execute(
            text(
                f"CREATE INDEX IF NOT EXISTS {PARENT_PART_NUMBER_INDEX} "
                f"ON {BLANKS_TABLE} ({PARENT_PART_NUMBER_COLUMN})"
            )
        )
    return (
        f"已 ALTER：{BLANKS_TABLE} 追加列 {PARENT_PART_NUMBER_COLUMN}，"
        f"已从父表回填，并创建索引 {PARENT_PART_NUMBER_INDEX}"
    )


def main() -> int:
    engine = DatabaseConfig.get_engine()
    url = str(engine.url)
    if not url.startswith("sqlite"):
        print(f"本脚本仅支持 SQLite，当前 DATABASE_URL={url}", file=sys.stderr)
        return 1

    print(f"目标库: {url}")
    print(_ensure_is_tailor_welded_column(engine))
    print(_ensure_tailor_weld_blanks_table(engine))
    print(_ensure_parent_part_number_column(engine))
    print("迁移完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
