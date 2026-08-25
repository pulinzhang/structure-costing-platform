"""
数据库配置模块
提供 SQLAlchemy 数据库连接和会话管理

主业务库（DatabaseConfig）与辅助库（AuxiliaryDatabaseConfig）隔离：
无 Redis 时，辅助库承载会话 Token、异步任务进度等短生命周期数据，
SQLite 使用独立文件，写入不受主业务长事务锁影响。
"""

from typing import Generator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.timezone import CHINA_TZ_NAME
from app.config import settings
from app.utils.logging_config import get_logger


logger = get_logger("database")


class Base(DeclarativeBase):
    """主业务库 ORM 基类。"""


class AuxiliaryBase(DeclarativeBase):
    """辅助库 ORM 基类（Token / 异步任务等）。"""


def _configure_sqlite_connection(dbapi_connection: object, connection_record: object) -> None:
    """SQLite：外键 + WAL；时间按东八区墙钟由应用层 now() 写入。"""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def _configure_postgres_connection(dbapi_connection: object, connection_record: object) -> None:
    """PostgreSQL：会话时区固定为东八区。"""
    cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
    cursor.execute(f"SET TIME ZONE '{CHINA_TZ_NAME}'")
    cursor.close()


def _create_engine_for_url(database_url: str, *, label: str) -> Engine:
    """按 URL 创建引擎（SQLite / PostgreSQL）。"""
    if "sqlite" in database_url:
        connect_args = {
            "check_same_thread": False,
            "timeout": 30,
        }
        if "mode=memory" in database_url or database_url.endswith(":memory:"):
            engine = create_engine(
                database_url,
                connect_args=connect_args,
                poolclass=StaticPool,
                echo=settings.IS_DEBUG,
            )
        else:
            engine = create_engine(
                database_url,
                connect_args=connect_args,
                echo=settings.IS_DEBUG,
            )
        event.listen(engine, "connect", _configure_sqlite_connection)
        logger.info(
            "%s SQLite 引擎创建成功: %s（业务时区 %s）",
            label,
            database_url,
            CHINA_TZ_NAME,
        )
        return engine

    engine = create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=settings.IS_DEBUG,
    )
    event.listen(engine, "connect", _configure_postgres_connection)
    logger.info("%s PostgreSQL 引擎创建成功（TIME ZONE %s）", label, CHINA_TZ_NAME)
    return engine


class DatabaseConfig:
    """主业务数据库配置"""

    _engine: Engine | None = None
    _session_factory: sessionmaker[Session] | None = None

    @classmethod
    def get_engine(cls) -> Engine:
        if cls._engine is None:
            cls._engine = _create_engine_for_url(
                settings.DATABASE_URL,
                label="主业务库",
            )
        return cls._engine

    @classmethod
    def get_session_factory(cls) -> sessionmaker[Session]:
        if cls._session_factory is None:
            engine = cls.get_engine()
            cls._session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return cls._session_factory

    @classmethod
    def create_tables(cls) -> None:
        engine = cls.get_engine()
        Base.metadata.create_all(bind=engine)
        cls._ensure_sqlite_columns(engine)
        logger.info("主业务库表创建完成")

    @classmethod
    def _ensure_sqlite_columns(cls, engine: Engine) -> None:
        """为已有 SQLite 库补齐 create_all 不会添加的新列。"""
        if not str(engine.url).startswith("sqlite"):
            return
        from sqlalchemy import inspect, text

        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        weld_table = "bom_l0_welding_fees"
        if weld_table in table_names:
            weld_cols = {col["name"] for col in inspector.get_columns(weld_table)}
            if "weld_info_raw" not in weld_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {weld_table} ADD COLUMN weld_info_raw TEXT")
                    )
                logger.info("已为 %s 追加列 weld_info_raw", weld_table)
            if "other_fee" not in weld_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {weld_table} "
                            "ADD COLUMN other_fee NUMERIC(14, 4)"
                        )
                    )
                logger.info("已为 %s 追加列 other_fee", weld_table)
            if "final_l0_welding_fee" not in weld_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {weld_table} "
                            "ADD COLUMN final_l0_welding_fee NUMERIC(14, 4)"
                        )
                    )
                    conn.execute(
                        text(
                            f"UPDATE {weld_table} SET final_l0_welding_fee = "
                            "total_l0_welding_fee "
                            "WHERE final_l0_welding_fee IS NULL"
                        )
                    )
                logger.info("已为 %s 追加列 final_l0_welding_fee 并回填", weld_table)
            if "remark" not in weld_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE {weld_table} ADD COLUMN remark TEXT")
                    )
                logger.info("已为 %s 追加列 remark", weld_table)

        fee_table = "stamping_process_fees"
        if fee_table in table_names:
            fee_cols = {col["name"] for col in inspector.get_columns(fee_table)}
            if "is_tailor_welded" not in fee_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {fee_table} "
                            "ADD COLUMN is_tailor_welded BOOLEAN NOT NULL DEFAULT 0"
                        )
                    )
                    conn.execute(
                        text(
                            "CREATE INDEX IF NOT EXISTS "
                            "ix_stamping_process_fee_is_tailor_welded "
                            f"ON {fee_table} (is_tailor_welded)"
                        )
                    )
                    conn.execute(
                        text(
                            f"UPDATE {fee_table} SET is_tailor_welded = 1 "
                            "WHERE source_part_id IS NOT NULL AND EXISTS ("
                            "SELECT 1 FROM stamping_parts p "
                            f"WHERE p.id = {fee_table}.source_part_id "
                            "AND p.is_tailor_welded = 1"
                            ")"
                        )
                    )
                    conn.execute(
                        text(
                            f"UPDATE {fee_table} SET is_tailor_welded = 1 "
                            "WHERE is_tailor_welded = 0 AND EXISTS ("
                            "SELECT 1 FROM stamping_parts p "
                            f"WHERE p.location = {fee_table}.location "
                            f"AND p.stamping_supplier = {fee_table}.stamping_supplier "
                            f"AND p.vehicle_model = {fee_table}.vehicle_model "
                            f"AND p.version = {fee_table}.version "
                            f"AND p.part_number = {fee_table}.part_number "
                            "AND p.is_tailor_welded = 1"
                            ")"
                        )
                    )
                logger.info("已为 %s 追加列 is_tailor_welded 并回填", fee_table)
            if "other_fee" not in fee_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {fee_table} "
                            "ADD COLUMN other_fee NUMERIC(12, 3)"
                        )
                    )
                logger.info("已为 %s 追加列 other_fee", fee_table)
            if "manual_unit_price" in fee_cols:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {fee_table} DROP COLUMN manual_unit_price"
                        )
                    )
                logger.info("已从 %s 删除列 manual_unit_price", fee_table)

        config_table = "system_configs"
        if config_table in table_names:
            config_cols = {col["name"] for col in inspector.get_columns(config_table)}
            config_new_columns = (
                ("finished_finance_rate", "NUMERIC(8, 6) NOT NULL DEFAULT 0.02"),
                ("finished_management_rate", "NUMERIC(8, 6) NOT NULL DEFAULT 0.02"),
                (
                    "finished_warehouse_packaging_rate",
                    "NUMERIC(8, 6) NOT NULL DEFAULT 0.01",
                ),
                ("finished_scrap_rate", "NUMERIC(8, 6) NOT NULL DEFAULT 0.003"),
                (
                    "finished_pretax_profit_rate",
                    "NUMERIC(8, 6) NOT NULL DEFAULT 0.02",
                ),
            )
            for column_name, column_def in config_new_columns:
                if column_name in config_cols:
                    continue
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {config_table} "
                            f"ADD COLUMN {column_name} {column_def}"
                        )
                    )
                logger.info("已为 %s 追加列 %s", config_table, column_name)

        cost_table = "stamping_part_costs"
        if cost_table in table_names:
            cost_cols = {col["name"] for col in inspector.get_columns(cost_table)}
            cost_new_columns = (
                ("direct_cost", "NUMERIC(14, 6)"),
                ("finished_finance_fee", "NUMERIC(14, 6)"),
                ("finished_management_fee", "NUMERIC(14, 6)"),
                ("finished_warehouse_packaging_fee", "NUMERIC(14, 6)"),
                ("finished_pretax_profit_fee", "NUMERIC(14, 6)"),
            )
            for column_name, column_def in cost_new_columns:
                if column_name in cost_cols:
                    continue
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {cost_table} "
                            f"ADD COLUMN {column_name} {column_def}"
                        )
                    )
                logger.info("已为 %s 追加列 %s", cost_table, column_name)

        pkg_table = "bom_packaging_transport_fees"
        if pkg_table in table_names:
            pkg_cols = {col["name"] for col in inspector.get_columns(pkg_table)}
            pkg_new_columns = (
                ("excel_filename", "VARCHAR(255)"),
                ("sheet_name", "VARCHAR(100)"),
                ("excel_row", "INTEGER"),
            )
            for column_name, column_def in pkg_new_columns:
                if column_name in pkg_cols:
                    continue
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {pkg_table} "
                            f"ADD COLUMN {column_name} {column_def}"
                        )
                    )
                logger.info("已为 %s 追加列 %s", pkg_table, column_name)

        llm_report_table = "llm_analysis_reports"
        if llm_report_table in table_names:
            llm_cols = {col["name"] for col in inspector.get_columns(llm_report_table)}
            llm_new_columns = (
                ("trace_id", "VARCHAR(36)"),
                ("prompt_preview", "TEXT"),
                ("llm_response_preview", "TEXT"),
            )
            for column_name, column_def in llm_new_columns:
                if column_name in llm_cols:
                    continue
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            f"ALTER TABLE {llm_report_table} "
                            f"ADD COLUMN {column_name} {column_def}"
                        )
                    )
                logger.info("已为 %s 追加列 %s", llm_report_table, column_name)

        obsolete_table = "llm_monthly_cost_summary"
        if obsolete_table in table_names:
            with engine.begin() as conn:
                conn.execute(text(f"DROP TABLE {obsolete_table}"))
            logger.info("已删除废弃表 %s", obsolete_table)


class AuxiliaryDatabaseConfig:
    """
    辅助数据库配置（无 Redis 时的旁路存储）。

    承载：异步任务进度、登录 Token 等短生命周期数据。
    """

    _engine: Engine | None = None
    _session_factory: sessionmaker[Session] | None = None

    @classmethod
    def get_engine(cls) -> Engine:
        if cls._engine is None:
            cls._engine = _create_engine_for_url(
                settings.AUXILIARY_DATABASE_URL,
                label="辅助库",
            )
        return cls._engine

    @classmethod
    def get_session_factory(cls) -> sessionmaker[Session]:
        if cls._session_factory is None:
            engine = cls.get_engine()
            cls._session_factory = sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return cls._session_factory

    @classmethod
    def create_tables(cls) -> None:
        import app.models.async_task  # noqa: F401
        import app.models.settings  # noqa: F401

        engine = cls.get_engine()
        AuxiliaryBase.metadata.create_all(bind=engine)
        logger.info("辅助库表创建完成")


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：主业务 Session。"""
    session_factory = DatabaseConfig.get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_auxiliary_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：辅助库 Session（async_tasks / user_tokens 等）。"""
    session_factory = AuxiliaryDatabaseConfig.get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
