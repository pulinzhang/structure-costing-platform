"""
为已有库补齐冲次单价 / 焊接单价的审核字段。

教学交付默认 create_all 不升级旧表；若本地已有数据文件，启动前可执行：

  python -X utf8 -m scripts.add_audit_columns_tonnage_welding
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.config import settings

ROOT = Path(__file__).resolve().parents[1]

COLUMNS = [
    ("audit_status", "VARCHAR(20) NOT NULL DEFAULT 'pending'"),
    ("audited_by", "VARCHAR(50)"),
    ("audited_at", "DATETIME"),
    ("audit_remark", "TEXT"),
    ("reverse_audited_by", "VARCHAR(50)"),
    ("reverse_audited_at", "DATETIME"),
    ("reverse_audit_remark", "TEXT"),
]

TABLES = ("stamping_tonnage_price", "bom_welding_unit_price")


def _sqlite_path_from_url(url: str) -> Path | None:
    if not url.startswith("sqlite:///"):
        return None
    raw = url.removeprefix("sqlite:///")
    if raw.startswith("./"):
        return (ROOT / raw[2:]).resolve()
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def ensure_columns(db_path: Path) -> None:
    if not db_path.exists():
        print(f"跳过：库文件不存在 {db_path}")
        return
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        for table in TABLES:
            cur.execute(f"PRAGMA table_info({table})")
            existing = {row[1] for row in cur.fetchall()}
            if not existing:
                print(f"跳过：表不存在 {table}")
                continue
            for name, decl in COLUMNS:
                if name in existing:
                    continue
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
                print(f"已添加 {table}.{name}")
            cur.execute(
                f"UPDATE {table} SET audit_status = 'pending' "
                f"WHERE audit_status IS NULL OR audit_status = ''"
            )
            cur.execute(
                f"CREATE INDEX IF NOT EXISTS ix_{table}_audit_status "
                f"ON {table} (audit_status)"
            )
        conn.commit()
        print(f"完成：{db_path}")
    finally:
        conn.close()


def main() -> None:
    path = _sqlite_path_from_url(settings.DATABASE_URL)
    if path is None:
        print(f"当前 DATABASE_URL 非 SQLite，请手工 ALTER：{settings.DATABASE_URL}")
        return
    ensure_columns(path)


if __name__ == "__main__":
    main()
