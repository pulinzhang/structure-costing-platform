"""
为已有库补齐焊接工艺拆解明细的「标准工艺单位」列，并按标准工艺名回填。

教学交付默认 create_all 不升级旧表；若本地已有数据，启动前可执行：

  python -X utf8 -m scripts.add_welding_breakdown_standard_unit_column
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.common.bom.welding_standard_process import STANDARD_PROCESS_UNIT
from app.config import settings

ROOT = Path(__file__).resolve().parents[1]
TABLE = "bom_welding_process_breakdown_line"
COLUMN = "standard_process_unit"
COLUMN_DECL = "VARCHAR(20)"


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


def ensure_column(db_path: Path) -> None:
    if not db_path.exists():
        print(f"跳过：库文件不存在 {db_path}")
        return
    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({TABLE})")
        existing = {row[1] for row in cur.fetchall()}
        if not existing:
            print(f"跳过：表不存在 {TABLE}")
            return
        if COLUMN not in existing:
            cur.execute(f"ALTER TABLE {TABLE} ADD COLUMN {COLUMN} {COLUMN_DECL}")
            print(f"已添加 {TABLE}.{COLUMN}")
        else:
            print(f"已存在 {TABLE}.{COLUMN}")

        updated = 0
        for name, unit in STANDARD_PROCESS_UNIT.items():
            cur.execute(
                f"UPDATE {TABLE} SET {COLUMN} = ? "
                f"WHERE standard_process_name = ? "
                f"AND ({COLUMN} IS NULL OR {COLUMN} = '')",
                (unit, name),
            )
            updated += cur.rowcount
        conn.commit()
        print(f"回填标准单位 {updated} 行；完成：{db_path}")
    finally:
        conn.close()


def main() -> None:
    path = _sqlite_path_from_url(settings.DATABASE_URL)
    if path is None:
        print(f"当前 DATABASE_URL 非 SQLite，请手工 ALTER：{settings.DATABASE_URL}")
        return
    ensure_column(path)


if __name__ == "__main__":
    main()
