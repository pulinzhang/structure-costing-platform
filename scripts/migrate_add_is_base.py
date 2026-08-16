"""添加 is_base 字段到 steel_price_ladder_items 表。

用法（仓库根目录）::

    python -X utf8 -m scripts.migrate_add_is_base
"""

from sqlalchemy import text

from app.database import DatabaseConfig


def migrate() -> None:
    conn = DatabaseConfig.get_engine().connect()

    result = conn.execute(text("PRAGMA table_info(steel_price_ladder_items)"))
    columns = [row[1] for row in result.fetchall()]

    if "is_base" not in columns:
        conn.execute(
            text("ALTER TABLE steel_price_ladder_items ADD COLUMN is_base INTEGER DEFAULT 0")
        )
        conn.commit()
        print("字段 is_base 添加成功")
    else:
        print("字段 is_base 已存在，跳过")


if __name__ == "__main__":
    migrate()
