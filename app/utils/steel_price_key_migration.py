"""
钢材价格表主键迁移工具

业务主键从 (year, month, steel_type, grade, reference_spec, steel_mill, thickness)
变更为 (year, month, grade, thickness)。

SQLite 的 UNIQUE 约束无法直接修改；该工具在检测到旧约束时通过临时表重建
steel_prices 表并保留历史数据（冲突行保留旧记录）。
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.utils.logging_config import get_logger


logger = get_logger("steel_price_key_migration")

EXPECTED_KEY_COLUMNS = ("year", "month", "grade", "thickness")
LEGACY_KEY_COLUMNS = (
    "year",
    "month",
    "steel_type",
    "grade",
    "reference_spec",
    "steel_mill",
    "thickness",
)
TABLE_NAME = "steel_prices"


def _existing_unique_columns(conn, table_name: str) -> list[str] | None:
    """返回业务主键索引对应的列名集合；若不是业务键索引则返回 None。"""
    result = conn.execute(
        text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=:name"
        ),
        {"name": table_name},
    ).fetchone()
    if not result or not result[0]:
        return None
    create_sql = result[0].upper()
    if "UIX_STEEL_PRICE_BUSINESS_KEY" not in create_sql:
        return None
    marker = "UIX_STEEL_PRICE_BUSINESS_KEY"
    start = create_sql.find(marker)
    paren_start = create_sql.find("(", start)
    paren_end = create_sql.find(")", paren_start)
    if paren_start < 0 or paren_end < 0:
        return None
    inside = create_sql[paren_start + 1 : paren_end]
    return [token.strip().lower() for token in inside.split(",") if token.strip()]


def _table_columns(conn, table_name: str) -> list[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
    return [row[1] for row in rows]


def _legacy_columns_present(conn, table_name: str) -> bool:
    actual = set(_table_columns(conn, table_name))
    return {"reference_spec", "steel_mill", "steel_type"}.issubset(actual)


def run_steel_price_key_migration(engine: Engine) -> None:
    """检测并修复钢材价格表的主键结构。"""
    if engine.dialect.name != "sqlite":
        return

    with engine.connect() as conn:
        cols = _existing_unique_columns(conn, TABLE_NAME)
        if cols is None:
            return
        if cols == list(EXPECTED_KEY_COLUMNS):
            return
        if cols != list(LEGACY_KEY_COLUMNS):
            logger.warning(
                "steel_prices 业务主键结构与预期不符: existing=%s expected=%s，跳过迁移",
                cols,
                list(EXPECTED_KEY_COLUMNS),
            )
            return
        if not _legacy_columns_present(conn, TABLE_NAME):
            logger.warning("steel_prices 缺少历史字段，跳过主键迁移")
            return

        logger.info("检测到钢材价格表旧业务主键，开始重建以切换为 (year, month, grade, thickness)")

        conn.execute(text(
            "CREATE TABLE steel_prices__new ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "year INTEGER NOT NULL,"
            "month INTEGER NOT NULL,"
            "steel_type VARCHAR(50) NOT NULL,"
            "grade VARCHAR(100) NOT NULL,"
            "reference_spec VARCHAR(100) NOT NULL,"
            "steel_mill VARCHAR(100) NOT NULL,"
            "bid_price NUMERIC(14, 4) NOT NULL,"
            "thickness NUMERIC(10, 4) NOT NULL,"
            "thickness_adjustment NUMERIC(14, 4) NOT NULL,"
            "processing_fee NUMERIC(14, 4) NOT NULL,"
            "final_price_per_ton NUMERIC(14, 4) NOT NULL,"
            "remark TEXT,"
            "created_at DATETIME NOT NULL,"
            "updated_at DATETIME NOT NULL,"
            "CONSTRAINT uix_steel_price_business_key UNIQUE (year, month, grade, thickness)"
            ")"
        ))

        conn.execute(text(
            "INSERT INTO steel_prices__new ("
            "id, year, month, steel_type, grade, reference_spec, steel_mill,"
            " bid_price, thickness, thickness_adjustment, processing_fee, final_price_per_ton,"
            " remark, created_at, updated_at)"
            " SELECT id, year, month, steel_type, grade, reference_spec, steel_mill,"
            " bid_price, thickness, thickness_adjustment, processing_fee, final_price_per_ton,"
            " remark, created_at, updated_at FROM steel_prices"
            " WHERE id IN ("
            "  SELECT MAX(id) FROM steel_prices"
            "  GROUP BY year, month, grade, thickness"
            " )"
        ))

        conn.execute(text("DROP TABLE steel_prices"))
        conn.execute(text("ALTER TABLE steel_prices__new RENAME TO steel_prices"))
        conn.execute(text(
            "CREATE INDEX ix_steel_price_year_month ON steel_prices(year, month)"
        ))
        conn.execute(text("CREATE INDEX ix_steel_price_grade ON steel_prices(grade)"))
        conn.execute(text(
            "CREATE INDEX ix_steel_price_steel_type ON steel_prices(steel_type)"
        ))
        conn.commit()
        logger.info("钢材价格表主键迁移完成，新主键为 (year, month, grade, thickness)")
