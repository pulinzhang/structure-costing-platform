"""
数据库配置模块
提供 SQLAlchemy 数据库连接和会话管理

主业务库（DatabaseConfig）与辅助库（AuxiliaryDatabaseConfig）隔离：
无 Redis 时，辅助库承载会话 Token、异步任务进度等短生命周期数据，
SQLite 使用独立文件，写入不受主业务长事务锁影响。

表结构以 Model 为准。create_all 只建缺表，不重建外键、不回填、不给已有表补列或补索引。
"""

from collections.abc import Generator

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
            "timeout": settings.SQLITE_BUSY_TIMEOUT_SECONDS,
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
            "%s SQLite 引擎创建成功: %s（业务时区 %s，写锁等待 %s 秒）",
            label,
            database_url,
            CHINA_TZ_NAME,
            settings.SQLITE_BUSY_TIMEOUT_SECONDS,
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
        logger.info("主业务库表创建完成")

    @classmethod
    def dispose(cls) -> None:
        if cls._engine is not None:
            cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            logger.info("主业务库连接池已释放")


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
        import app.models.async_task
        import app.models.settings  # noqa: F401

        engine = cls.get_engine()
        AuxiliaryBase.metadata.create_all(bind=engine)
        logger.info("辅助库表创建完成")

    @classmethod
    def dispose(cls) -> None:
        if cls._engine is not None:
            cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            logger.info("辅助库连接池已释放")


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
