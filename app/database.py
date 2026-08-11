"""
数据库配置模块
提供 SQLAlchemy 数据库连接和会话管理

主业务库（DatabaseConfig）与异步任务库（AsyncTaskDatabaseConfig）隔离：
SQLite 使用独立文件，进度写入不会被业务长事务锁死。
"""

from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.utils.logging_config import get_logger


logger = get_logger("database")

Base = declarative_base()
AsyncTaskBase = declarative_base()


def _configure_sqlite_connection(dbapi_connection, connection_record):
    """SQLite：外键 + WAL + 写锁等待更友好"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


def _create_engine_for_url(database_url: str, *, label: str):
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
                echo=settings.DEBUG,
            )
        else:
            engine = create_engine(
                database_url,
                connect_args=connect_args,
                echo=settings.DEBUG,
            )
        event.listen(engine, "connect", _configure_sqlite_connection)
        logger.info("%s SQLite 引擎创建成功: %s", label, database_url)
        return engine

    engine = create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )
    logger.info("%s PostgreSQL 引擎创建成功", label)
    return engine


class DatabaseConfig:
    """主业务数据库配置"""

    _engine = None
    _session_factory = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            cls._engine = _create_engine_for_url(
                settings.DATABASE_URL,
                label="主业务库",
            )
        return cls._engine

    @classmethod
    def get_session_factory(cls) -> sessionmaker:
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


class AsyncTaskDatabaseConfig:
    """异步任务独立库配置（与主业务库隔离）。"""

    _engine = None
    _session_factory = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            cls._engine = _create_engine_for_url(
                settings.ASYNC_TASK_DATABASE_URL,
                label="异步任务库",
            )
        return cls._engine

    @classmethod
    def get_session_factory(cls) -> sessionmaker:
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

        engine = cls.get_engine()
        AsyncTaskBase.metadata.create_all(bind=engine)
        logger.info("异步任务库表创建完成")


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：主业务 Session（带事务，供业务导入使用）。"""
    session_factory = DatabaseConfig.get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
