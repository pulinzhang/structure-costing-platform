# -*- coding: utf-8 -*-
"""创建 stamping_process_fee_calc_logs 表。"""

from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "stamping_costing.db"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS stamping_process_fee_calc_logs (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    calc_batch_id VARCHAR(64) NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    location VARCHAR(50) NOT NULL,
    stamping_supplier VARCHAR(50) NOT NULL,
    vehicle_model VARCHAR(50),
    version VARCHAR(20),
    status VARCHAR(20) NOT NULL DEFAULT 'failed',
    total_parts INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    zero_fee_count INTEGER NOT NULL DEFAULT 0,
    skipped_approved_count INTEGER NOT NULL DEFAULT 0,
    detail_text TEXT NOT NULL DEFAULT '',
    started_at DATETIME NOT NULL,
    finished_at DATETIME,
    operator_id INTEGER,
    operator_name VARCHAR(50),
    created_at DATETIME NOT NULL,
    created_by VARCHAR(50),
    updated_at DATETIME NOT NULL,
    updated_by VARCHAR(50)
)
"""


def migrate() -> None:
    if not DB_PATH.exists():
        print(f"数据库不存在，跳过: {DB_PATH}")
        return
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(CREATE_SQL)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_spf_calc_log_batch "
            "ON stamping_process_fee_calc_logs (calc_batch_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_spf_calc_log_year "
            "ON stamping_process_fee_calc_logs (year)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_spf_calc_log_status "
            "ON stamping_process_fee_calc_logs (status)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_spf_calc_processing "
            "ON stamping_process_fee_calc_logs(year, location, stamping_supplier) "
            "WHERE status = 'processing'"
        )
        conn.commit()
        print("stamping_process_fee_calc_logs 表就绪")
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
