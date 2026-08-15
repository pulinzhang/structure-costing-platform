# -*- coding: utf-8 -*-
"""迁移：stamping_process_fees 增加手工调整/最终加工费，processing_fee 可空。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "stamping_costing.db"


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {r[1] for r in rows}


def _column_notnull(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    for row in rows:
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
            print("表 stamping_process_fees 不存在，跳过（create_all 会按新模型建表）")
            return

        cols = _column_names(conn, "stamping_process_fees")
        need_rebuild = _column_notnull(conn, "stamping_process_fees", "processing_fee")
        need_add_manual = "manual_unit_price" not in cols
        need_add_final = "final_processing_fee" not in cols
        need_add_reason = "calc_fail_reason" not in cols
        need_add_remark = "remark" not in cols

        if need_rebuild:
            print("重建表以使 processing_fee 可空…")
            conn.execute("DROP TABLE IF EXISTS stamping_process_fees__new")
            conn.execute(
                """
                CREATE TABLE stamping_process_fees__new (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    location VARCHAR(50) NOT NULL,
                    stamping_supplier VARCHAR(50),
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
                        year, location, stamping_supplier, vehicle_model, version, part_number
                    )
                )
                """
            )
            select_manual = (
                "manual_unit_price" if "manual_unit_price" in cols else "NULL"
            )
            select_final = (
                "final_processing_fee" if "final_processing_fee" in cols else "NULL"
            )
            select_reason = (
                "calc_fail_reason" if "calc_fail_reason" in cols else "NULL"
            )
            select_remark = "remark" if "remark" in cols else "NULL"
            conn.execute(
                f"""
                INSERT INTO stamping_process_fees__new (
                    id, year, location, stamping_supplier, vehicle_model, version,
                    part_number, part_name, processing_fee, process_count,
                    manual_unit_price, final_processing_fee, calc_fail_reason, remark,
                    created_at, created_by, updated_at, updated_by
                )
                SELECT
                    id, year, location, stamping_supplier, vehicle_model, version,
                    part_number, part_name, processing_fee, process_count,
                    {select_manual}, {select_final}, {select_reason}, {select_remark},
                    created_at, created_by, updated_at, updated_by
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
        else:
            alters: list[str] = []
            if need_add_manual:
                alters.append(
                    "ALTER TABLE stamping_process_fees "
                    "ADD COLUMN manual_unit_price NUMERIC(12,3)"
                )
            if need_add_final:
                alters.append(
                    "ALTER TABLE stamping_process_fees "
                    "ADD COLUMN final_processing_fee NUMERIC(12,3)"
                )
            if need_add_reason:
                alters.append(
                    "ALTER TABLE stamping_process_fees "
                    "ADD COLUMN calc_fail_reason TEXT"
                )
            if need_add_remark:
                alters.append(
                    "ALTER TABLE stamping_process_fees "
                    "ADD COLUMN remark TEXT"
                )
            for sql in alters:
                conn.execute(sql)
                print(f"执行: {sql}")

        conn.execute(
            """
            UPDATE stamping_process_fees
            SET final_processing_fee = COALESCE(manual_unit_price, processing_fee)
            WHERE final_processing_fee IS NULL
            """
        )
        conn.commit()
        print("迁移完成")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
