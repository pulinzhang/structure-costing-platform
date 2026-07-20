"""
数据库自动迁移工具
在应用启动时自动对比 Model 定义与实际表结构，执行必要的 ALTER TABLE 操作
仅支持 SQLite，且只做 ADD COLUMN，不做 DROP COLUMN（防止数据丢失）
"""

from typing import Dict, List
from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine

from app.database import Base
from app.utils.logging_config import get_logger


logger = get_logger("db_migration")


SQLITE_TYPE_MAP = {
    "INTEGER": "INTEGER",
    "BIGINT": "INTEGER",
    "SMALLINT": "INTEGER",
    "TINYINT": "INTEGER",
    "NUMERIC": "REAL",
    "FLOAT": "REAL",
    "DOUBLE": "REAL",
    "VARCHAR": "TEXT",
    "CHAR": "TEXT",
    "TEXT": "TEXT",
    "BLOB": "BLOB",
    "BOOLEAN": "INTEGER",
    "DATETIME": "TEXT",
    "DATE": "TEXT",
}


def _sqlite_type(sqlalchemy_type: str) -> str:
    """将 SQLAlchemy 类型名映射为 SQLite 类型名"""
    base = sqlalchemy_type.upper().split("(")[0].strip()
    return SQLITE_TYPE_MAP.get(base, "TEXT")


def _get_model_columns(table) -> Dict[str, dict]:
    """从 Model 的 Table 对象提取列信息"""
    columns = {}
    for col in table.columns:
        col_name = col.name
        sql_type = str(col.type)
        nullable = col.nullable
        default = col.default.arg if col.default and hasattr(col.default, "arg") else None
        is_primary = col.primary_key

        columns[col_name] = {
            "type": _sqlite_type(sql_type),
            "nullable": nullable,
            "default": default,
            "primary": is_primary,
        }
    return columns


def _get_actual_columns(engine: Engine, table_name: str) -> Dict[str, dict]:
    """从 SQLite 实际表结构提取列信息"""
    with engine.connect() as conn:
        result = conn.execute(
            text(f"PRAGMA table_info({table_name})")
        )
        columns = {}
        for row in result:
            col_name = row[1]
            col_type = row[2]
            notnull = row[3]
            dflt_value = row[4]
            pk = row[5]
            columns[col_name] = {
                "type": col_type,
                "nullable": not notnull,
                "default": dflt_value,
                "primary": pk > 0 if pk is not None else False,
            }
        return columns


def _migrate_table(engine: Engine, table) -> List[str]:
    """
    对比单个表的 Model 定义与实际结构，执行必要的 ADD COLUMN
    返回本次执行的 SQL 语句列表
    """
    table_name = table.name
    model_cols = _get_model_columns(table)
    actual_cols = _get_actual_columns(engine, table_name)

    if not actual_cols:
        logger.warning(f"表 {table_name} 不存在，跳过迁移")
        return []

    sqls: List[str] = []
    with engine.connect() as conn:
        for col_name, model_info in model_cols.items():
            if col_name in actual_cols:
                continue
            col_type = model_info["type"]
            nullable = "" if model_info["nullable"] else "NOT NULL"
            default = ""
            if model_info["default"] is not None:
                default_val = model_info["default"]
                if isinstance(default_val, str):
                    default = f" DEFAULT '{default_val}'"
                else:
                    default = f" DEFAULT {default_val}"
            sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}{nullable}{default}"
            sqls.append(sql)
            conn.execute(text(sql))
            logger.info(f"  + ADD COLUMN {table_name}.{col_name} ({col_type})")
        conn.commit()
    return sqls


def run_auto_migration():
    """
    扫描 Base.metadata 中所有表，对比实际数据库结构
    自动执行 ADD COLUMN（仅补充缺失列，不删除任何列）
    """
    from app.database import DatabaseConfig

    engine = DatabaseConfig.get_engine()

    dialect = engine.dialect.name
    if dialect != "sqlite":
        logger.info(f"[db_migration] 当前数据库为 {dialect}，跳过自动迁移")
        return

    tables = list(Base.metadata.tables.values())
    if not tables:
        logger.info("[db_migration] 未发现任何 Model 定义")
        return

    logger.info(f"[db_migration] 开始扫描 {len(tables)} 张表...")
    total_sqls = 0
    for table in tables:
        sqls = _migrate_table(engine, table)
        total_sqls += len(sqls)
        if not sqls:
            logger.info(f"  ✓ {table.name} 结构一致")

    if total_sqls > 0:
        logger.info(f"[db_migration] 完成，共执行 {total_sqls} 条 ALTER TABLE")
    else:
        logger.info("[db_migration] 完成，所有表结构已同步")
