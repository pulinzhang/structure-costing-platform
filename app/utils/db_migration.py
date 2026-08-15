"""
数据库自动迁移工具
在应用启动时自动对比 Model 定义与实际表结构，执行必要的 ALTER TABLE 操作
仅支持 SQLite，且只做 ADD COLUMN，不做 DROP COLUMN（防止数据丢失）
"""

from typing import Any, Dict, List
from sqlalchemy import text
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


def _get_model_columns(table: Any) -> Dict[str, dict[str, Any]]:
    """从 Model 的 Table 对象提取列信息"""
    columns = {}
    for col in table.columns:
        col_name = col.name
        sql_type = str(col.type)
        nullable = col.nullable
        default = None
        if col.default is not None and hasattr(col.default, "arg"):
            default = col.default.arg
        is_primary = col.primary_key

        columns[col_name] = {
            "type": _sqlite_type(sql_type),
            "nullable": nullable,
            "default": default,
            "primary": is_primary,
        }
    return columns


def _get_actual_columns(engine: Engine, table_name: str) -> Dict[str, dict[str, Any]]:
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


def _build_add_column_sql(table_name: str, col_name: str, model_info: dict[str, Any]) -> str:
    """
    生成 SQLite ADD COLUMN。

    SQLite 限制：ADD COLUMN 的 DEFAULT 必须是常量（不能用 CURRENT_TIMESTAMP / 函数）。
    因此 callable 默认值（如 datetime.now）不加 SQL DEFAULT；
    若原定义 NOT NULL 且无常量默认值，则退化为可空列，由 ORM 在写入时填充。
    """
    col_type = model_info["type"]
    is_nullable = bool(model_info["nullable"])
    default_val = model_info["default"]

    default_sql = ""
    if default_val is not None and not callable(default_val):
        if isinstance(default_val, str):
            default_sql = f" DEFAULT '{default_val}'"
        elif isinstance(default_val, bool):
            default_sql = f" DEFAULT {1 if default_val else 0}"
        else:
            default_sql = f" DEFAULT {default_val}"

    # NOT NULL 新列必须有常量 DEFAULT，否则改为可空
    if not is_nullable and not default_sql:
        is_nullable = True

    nullable_sql = "" if is_nullable else " NOT NULL"
    return (
        f"ALTER TABLE {table_name} ADD COLUMN {col_name} "
        f"{col_type}{nullable_sql}{default_sql}"
    )


def _migrate_table(engine: Engine, table: Any) -> List[str]:
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
            sql = _build_add_column_sql(table_name, col_name, model_info)
            sqls.append(sql)
            try:
                conn.execute(text(sql))
                logger.info(f"  + ADD COLUMN {table_name}.{col_name} ({model_info['type']})")
            except Exception as ex:
                logger.warning(f"  ! ADD COLUMN {table_name}.{col_name} 失败: {ex}")
        conn.commit()
    return sqls


def run_auto_migration() -> None:
    """
    扫描主库 Base + 辅助库 AuxiliaryBase，对比实际表结构，
    自动执行 ADD COLUMN（仅补充缺失列，不删除任何列）。
    """
    from app.database import AuxiliaryBase, AuxiliaryDatabaseConfig, DatabaseConfig

    # 确保辅助库模型已注册
    import app.models.async_task  # noqa: F401
    import app.models.user_token  # noqa: F401

    targets = [
        ("主业务库", DatabaseConfig.get_engine(), list(Base.metadata.tables.values())),
        (
            "辅助库",
            AuxiliaryDatabaseConfig.get_engine(),
            list(AuxiliaryBase.metadata.tables.values()),
        ),
    ]

    for label, engine, tables in targets:
        dialect = engine.dialect.name
        if dialect != "sqlite":
            logger.info("[db_migration] %s 当前为 %s，跳过自动迁移", label, dialect)
            continue
        if not tables:
            logger.info("[db_migration] %s 未发现任何 Model 定义", label)
            continue

        logger.info("[db_migration] %s 开始扫描 %s 张表...", label, len(tables))
        total_sqls = 0
        for table in tables:
            sqls = _migrate_table(engine, table)
            total_sqls += len(sqls)
            if not sqls:
                logger.info("  ✓ %s 结构一致", table.name)

        if total_sqls > 0:
            logger.info(
                "[db_migration] %s 完成，共执行 %s 条 ALTER TABLE",
                label,
                total_sqls,
            )
        else:
            logger.info("[db_migration] %s 完成，所有表结构已同步", label)

    # 主库一次性数据补丁：operation_logs 早期用 SQLite CURRENT_TIMESTAMP(UTC)
    _patch_operation_logs_utc_to_china(DatabaseConfig.get_engine())


def _patch_operation_logs_utc_to_china(engine: Engine) -> None:
    """将历史 operation_logs.created_at 从 UTC 纠正为东八区墙钟（仅执行一次）。"""
    if engine.dialect.name != "sqlite":
        return
    patch_id = "operation_logs_created_at_utc_to_china_v1"
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS schema_patches (
                        patch_id TEXT PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    )
                    """
                )
            )
            existed = conn.execute(
                text("SELECT 1 FROM schema_patches WHERE patch_id = :pid"),
                {"pid": patch_id},
            ).first()
            if existed:
                return

            tables = {
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='table' AND name='operation_logs'"
                    )
                )
            }
            if "operation_logs" not in tables:
                conn.execute(
                    text(
                        "INSERT INTO schema_patches(patch_id, applied_at) "
                        "VALUES (:pid, :ts)"
                    ),
                    {"pid": patch_id, "ts": _patch_timestamp()},
                )
                return

            result = conn.execute(
                text(
                    "UPDATE operation_logs "
                    "SET created_at = datetime(created_at, '+8 hours')"
                )
            )
            conn.execute(
                text(
                    "INSERT INTO schema_patches(patch_id, applied_at) "
                    "VALUES (:pid, :ts)"
                ),
                {"pid": patch_id, "ts": _patch_timestamp()},
            )
            logger.info(
                "[db_migration] 已纠正 operation_logs.created_at UTC→东八区，影响 %s 行",
                result.rowcount if result.rowcount is not None else "?",
            )
    except Exception:
        logger.exception("[db_migration] operation_logs 时区补丁失败")


def _patch_timestamp() -> str:
    from app.common.timezone import now

    return now().strftime("%Y-%m-%d %H:%M:%S")
