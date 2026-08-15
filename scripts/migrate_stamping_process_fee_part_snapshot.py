# -*- coding: utf-8 -*-
"""迁移：stamping_process_fees 增加零件主表快照字段（材料/料片/工艺等）。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "stamping_costing.db"

COLUMNS = [
    ("source_part_id", "INTEGER"),
    ("seq_no", "INTEGER"),
    ("material", "VARCHAR(50)"),
    ("thickness", "NUMERIC(10, 4)"),
    ("part_weight", "NUMERIC(12, 4)"),
    ("sheet_length", "NUMERIC(10, 2)"),
    ("sheet_width", "NUMERIC(10, 2)"),
    ("parts_per_sheet", "INTEGER"),
    ("sheet_type", "VARCHAR(50)"),
    ("die_type", "VARCHAR(50)"),
    ("process_method", "VARCHAR(50)"),
    ("automation", "VARCHAR(20)"),
    ("part_remark", "TEXT"),
    ("sketch_url", "VARCHAR(500)"),
    ("excel_filename", "VARCHAR(255)"),
]


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def migrate() -> None:
    if not DB_PATH.exists():
        print(f"数据库不存在，跳过: {DB_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "stamping_process_fees" not in tables:
            print("表 stamping_process_fees 不存在，跳过")
            return

        cols = _column_names(conn, "stamping_process_fees")
        added = 0
        for name, ddl in COLUMNS:
            if name in cols:
                print(f"已存在列 {name}，跳过")
                continue
            conn.execute(
                f"ALTER TABLE stamping_process_fees ADD COLUMN {name} {ddl}"
            )
            print(f"已添加列 {name}")
            added += 1

        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_stamping_process_fee_material "
            "ON stamping_process_fees (material)"
        )
        conn.commit()
        print(f"零件快照字段迁移完成（新增 {added} 列）")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
