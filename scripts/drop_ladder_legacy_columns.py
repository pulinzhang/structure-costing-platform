"""删除 steel_price_ladder_items 中的旧单维度字段（min_val/min_operator/max_val/max_operator）及对应索引。"""
from sqlalchemy import text

from app.database import DatabaseConfig


DDL_STATEMENTS = [
    "DROP INDEX IF EXISTS ix_ladder_min_val",
    "DROP INDEX IF EXISTS ix_ladder_max_val",
    "ALTER TABLE steel_price_ladder_items DROP COLUMN min_val",
    "ALTER TABLE steel_price_ladder_items DROP COLUMN min_operator",
    "ALTER TABLE steel_price_ladder_items DROP COLUMN max_val",
    "ALTER TABLE steel_price_ladder_items DROP COLUMN max_operator",
]


def main() -> None:
    engine = DatabaseConfig.get_engine()
    with engine.begin() as conn:
        for sql in DDL_STATEMENTS:
            print(f"执行: {sql}")
            conn.execute(text(sql))
    print("完成：已删除旧字段及其索引。")


if __name__ == "__main__":
    main()