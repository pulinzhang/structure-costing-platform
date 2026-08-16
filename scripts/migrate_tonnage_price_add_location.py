"""
迁移：stamping_tonnage_price 增加 location（采购基地）维度
- 若缺列 / 值为空 / 唯一约束仍是旧的 (year, tonnage)：重建表
- 存量空 location 回填为「青岛」
- 唯一约束改为 (location, year, tonnage)

用法（仓库根目录）::

    python -X utf8 -m scripts.migrate_tonnage_price_add_location
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.config import settings
from app.database import DatabaseConfig

DEFAULT_LOCATION = "青岛"


def _needs_migrate(conn: Connection) -> bool:
    cols = conn.execute(text("PRAGMA table_info(stamping_tonnage_price)")).fetchall()
    if not cols:
        print("表 stamping_tonnage_price 不存在，跳过（create_all 会按新模型建表）")
        return False

    col_map = {c[1]: c for c in cols}
    if "location" not in col_map:
        print("缺少 location 列，需要迁移")
        return True

    # notnull flag: PRAGMA table_info 第 4 列 (index 3)
    if not col_map["location"][3]:
        print("location 列可空，需要重建为 NOT NULL")
        return True

    ddl_row = conn.execute(
        text(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND name='stamping_tonnage_price'"
        )
    ).fetchone()
    ddl = (ddl_row[0] or "") if ddl_row else ""
    if "uix_location_year_tonnage_unique" not in ddl:
        print("唯一约束未升级为 (location, year, tonnage)，需要迁移")
        return True

    null_count = conn.execute(
        text(
            "SELECT COUNT(*) FROM stamping_tonnage_price "
            "WHERE location IS NULL OR TRIM(location) = ''"
        )
    ).scalar()
    if null_count:
        print(f"存在 {null_count} 条空 location，需要回填")
        return True

    print("location 维度已就绪，无需迁移")
    return False


def migrate() -> None:
    engine = DatabaseConfig.get_engine()
    print(f"DATABASE_URL={settings.DATABASE_URL}")

    with engine.begin() as conn:
        cols = conn.execute(text("PRAGMA table_info(stamping_tonnage_price)")).fetchall()
        if not cols:
            print("表 stamping_tonnage_price 不存在，跳过")
            return

        if not _needs_migrate(conn):
            return

        has_location = "location" in {c[1] for c in cols}
        print(f"重建表以规范 location（存量回填为「{DEFAULT_LOCATION}」）...")
        conn.execute(text("DROP TABLE IF EXISTS stamping_tonnage_price__new"))
        conn.execute(text("""
            CREATE TABLE stamping_tonnage_price__new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                location VARCHAR(50) NOT NULL,
                year INTEGER NOT NULL,
                tonnage INTEGER NOT NULL,
                price_per_stroke NUMERIC(12, 3) NOT NULL,
                created_at DATETIME NOT NULL,
                created_by VARCHAR(50),
                updated_at DATETIME NOT NULL,
                updated_by VARCHAR(50),
                CONSTRAINT uix_location_year_tonnage_unique
                    UNIQUE (location, year, tonnage)
            )
        """))

        if has_location:
            conn.execute(text(f"""
                INSERT INTO stamping_tonnage_price__new
                    (id, location, year, tonnage, price_per_stroke,
                     created_at, created_by, updated_at, updated_by)
                SELECT
                    id,
                    CASE
                        WHEN location IS NULL OR TRIM(location) = ''
                        THEN '{DEFAULT_LOCATION}'
                        ELSE location
                    END,
                    year, tonnage, price_per_stroke,
                    created_at, created_by, updated_at, updated_by
                FROM stamping_tonnage_price
            """))
        else:
            conn.execute(text(f"""
                INSERT INTO stamping_tonnage_price__new
                    (id, location, year, tonnage, price_per_stroke,
                     created_at, created_by, updated_at, updated_by)
                SELECT
                    id, '{DEFAULT_LOCATION}', year, tonnage, price_per_stroke,
                    created_at, created_by, updated_at, updated_by
                FROM stamping_tonnage_price
            """))

        conn.execute(text("DROP TABLE stamping_tonnage_price"))
        conn.execute(text(
            "ALTER TABLE stamping_tonnage_price__new RENAME TO stamping_tonnage_price"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_tonnage_price_location "
            "ON stamping_tonnage_price (location)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_tonnage_price_year "
            "ON stamping_tonnage_price (year)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_tonnage_price_tonnage "
            "ON stamping_tonnage_price (tonnage)"
        ))

        new_cols = conn.execute(text("PRAGMA table_info(stamping_tonnage_price)")).fetchall()
        print(f"迁移完成，列: {[c[1] for c in new_cols]}")
        count = conn.execute(text(
            "SELECT COUNT(*) FROM stamping_tonnage_price WHERE location = :loc"
        ), {"loc": DEFAULT_LOCATION}).scalar()
        print(f"回填为「{DEFAULT_LOCATION}」的记录数: {count}")


if __name__ == "__main__":
    migrate()
