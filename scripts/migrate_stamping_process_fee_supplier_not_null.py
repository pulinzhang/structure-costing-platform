# -*- coding: utf-8 -*-
"""迁移：stamping_process_fees.stamping_supplier 改为 NOT NULL（冲压工厂必填）。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "stamping_costing.db"


def _column_notnull(conn: sqlite3.Connection, table: str, column: str) -> bool:
    for row in conn.execute(f"PRAGMA table_info({table})").fetchall():
        if row[1] == column:
            return bool(row[3])
    return False


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

        if _column_notnull(conn, "stamping_process_fees", "stamping_supplier"):
            print("stamping_supplier 已是 NOT NULL，跳过")
            return

        null_count = conn.execute(
            "SELECT COUNT(*) FROM stamping_process_fees "
            "WHERE stamping_supplier IS NULL OR TRIM(stamping_supplier) = ''"
        ).fetchone()[0]
        if null_count:
            raise RuntimeError(
                f"存在 {null_count} 条缺少冲压工厂的记录，请先补齐或删除后再迁移"
            )

        print("重建表以使 stamping_supplier NOT NULL…")
        conn.execute("DROP TABLE IF EXISTS stamping_process_fees__new")
        conn.execute(
            """
            CREATE TABLE stamping_process_fees__new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                location VARCHAR(50) NOT NULL,
                stamping_supplier VARCHAR(50) NOT NULL,
                vehicle_model VARCHAR(50) NOT NULL,
                version VARCHAR(20) NOT NULL,
                part_number VARCHAR(50) NOT NULL,
                part_name VARCHAR(200),
                processing_fee NUMERIC(12, 3),
                process_count INTEGER NOT NULL DEFAULT 0,
                manual_unit_price NUMERIC(12, 3),
                final_processing_fee NUMERIC(12, 3),
                calc_fail_reason TEXT,
                remark TEXT,
                created_at DATETIME NOT NULL,
                created_by VARCHAR(50),
                updated_at DATETIME NOT NULL,
                updated_by VARCHAR(50),
                CONSTRAINT uix_stamping_process_fee_unique_key UNIQUE (
                    year, location, stamping_supplier,
                    vehicle_model, version, part_number
                )
            )
            """
        )
        conn.execute(
            """
            INSERT INTO stamping_process_fees__new (
                id, year, location, stamping_supplier, vehicle_model, version,
                part_number, part_name, processing_fee, process_count,
                manual_unit_price, final_processing_fee, calc_fail_reason,
                remark, created_at, created_by, updated_at, updated_by
            )
            SELECT
                id, year, location, stamping_supplier, vehicle_model, version,
                part_number, part_name, processing_fee, process_count,
                manual_unit_price, final_processing_fee, calc_fail_reason,
                remark, created_at, created_by, updated_at, updated_by
            FROM stamping_process_fees
            """
        )
        conn.execute("DROP TABLE stamping_process_fees")
        conn.execute(
            "ALTER TABLE stamping_process_fees__new RENAME TO stamping_process_fees"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_stamping_process_fee_year "
            "ON stamping_process_fees (year)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_stamping_process_fee_location "
            "ON stamping_process_fees (location)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_stamping_process_fee_part_number "
            "ON stamping_process_fees (part_number)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_stamping_process_fee_year_location "
            "ON stamping_process_fees (year, location)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_stamping_process_fee_supplier "
            "ON stamping_process_fees (stamping_supplier)"
        )
        conn.commit()
        print("迁移完成：stamping_supplier 现为 NOT NULL")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
