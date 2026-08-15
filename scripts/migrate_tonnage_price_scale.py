"""
迁移：stamping_tonnage_price.price_per_stroke 精度由 Numeric(12,4) 改为 Numeric(12,3)
SQLite 不支持直接改列类型，采用建新表 → 拷贝 → 替换。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.config import settings
from app.database import DatabaseConfig


def migrate():
    engine = DatabaseConfig.get_engine()
    print(f"DATABASE_URL={settings.DATABASE_URL}")

    with engine.begin() as conn:
        cols = conn.execute(text("PRAGMA table_info(stamping_tonnage_price)")).fetchall()
        if not cols:
            print("表 stamping_tonnage_price 不存在，跳过（create_all 会按新模型建表）")
            return

        price_col = next((c for c in cols if c[1] == "price_per_stroke"), None)
        print(f"当前 price_per_stroke 类型: {price_col[2] if price_col else 'N/A'}")

        type_norm = (price_col[2] or "").replace(" ", "").upper() if price_col else ""
        if "NUMERIC(12,3)" in type_norm:
            print("已是 NUMERIC(12,3)，无需迁移")
            return

        print("重建表以应用 NUMERIC(12,3)...")
        conn.execute(text("DROP TABLE IF EXISTS stamping_tonnage_price__new"))
        conn.execute(text("""
            CREATE TABLE stamping_tonnage_price__new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                tonnage INTEGER NOT NULL,
                price_per_stroke NUMERIC(12, 3) NOT NULL,
                created_at DATETIME NOT NULL,
                created_by VARCHAR(50),
                updated_at DATETIME NOT NULL,
                updated_by VARCHAR(50),
                CONSTRAINT uix_year_tonnage_unique UNIQUE (year, tonnage)
            )
        """))
        conn.execute(text("""
            INSERT INTO stamping_tonnage_price__new
                (id, year, tonnage, price_per_stroke, created_at, created_by, updated_at, updated_by)
            SELECT
                id, year, tonnage,
                ROUND(CAST(price_per_stroke AS REAL), 3),
                created_at, created_by, updated_at, updated_by
            FROM stamping_tonnage_price
        """))
        conn.execute(text("DROP TABLE stamping_tonnage_price"))
        conn.execute(text("ALTER TABLE stamping_tonnage_price__new RENAME TO stamping_tonnage_price"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tonnage_price_year ON stamping_tonnage_price (year)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tonnage_price_tonnage ON stamping_tonnage_price (tonnage)"))

        new_cols = conn.execute(text("PRAGMA table_info(stamping_tonnage_price)")).fetchall()
        price_col = next((c for c in new_cols if c[1] == "price_per_stroke"), None)
        print(f"迁移完成，price_per_stroke 类型: {price_col[2] if price_col else 'N/A'}")


if __name__ == "__main__":
    migrate()
