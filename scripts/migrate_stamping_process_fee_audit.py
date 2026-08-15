# -*- coding: utf-8 -*-
"""迁移：stamping_process_fees 增加审核字段。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "stamping_costing.db"

COLUMNS = [
    ("audit_status", "VARCHAR(20) NOT NULL DEFAULT 'pending'"),
    ("audited_by", "VARCHAR(50)"),
    ("audited_at", "DATETIME"),
    ("audit_remark", "TEXT"),
    ("reverse_audited_by", "VARCHAR(50)"),
    ("reverse_audited_at", "DATETIME"),
    ("reverse_audit_remark", "TEXT"),
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
        for name, ddl in COLUMNS:
            if name in cols:
                print(f"已存在列 {name}，跳过")
                continue
            conn.execute(
                f"ALTER TABLE stamping_process_fees ADD COLUMN {name} {ddl}"
            )
            print(f"已添加列 {name}")

        conn.execute(
            "UPDATE stamping_process_fees "
            "SET audit_status = 'pending' "
            "WHERE audit_status IS NULL OR TRIM(audit_status) = ''"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_stamping_process_fee_audit_status "
            "ON stamping_process_fees (audit_status)"
        )
        conn.commit()
        print("审核字段迁移完成")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
