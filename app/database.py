"""
数据库配置模块
提供 SQLAlchemy 数据库连接和会话管理
"""

from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.utils.logging_config import get_logger


logger = get_logger("database")

Base = declarative_base()


class DatabaseConfig:
    """
    数据库配置类
    管理数据库连接引擎和会话工厂
    """

    _engine = None
    _session_factory = None

    @classmethod
    def get_engine(cls):
        """
        获取数据库引擎
        根据配置创建合适的引擎实例

        Returns:
            SQLAlchemy Engine 实例
        """
        if cls._engine is None:
            cls._create_engine()
        return cls._engine

    @classmethod
    def _create_engine(cls) -> None:
        """
        创建数据库引擎
        根据数据库 URL 类型选择合适的配置
        """
        if "sqlite" in settings.DATABASE_URL:
            cls._create_sqlite_engine()
        else:
            cls._create_postgres_engine()

    @classmethod
    def _create_sqlite_engine(cls) -> None:
        """
        创建 SQLite 数据库引擎
        配置外键支持和连接池
        """
        connect_args = {"check_same_thread": False}

        if "mode=memory" in settings.DATABASE_URL:
            cls._engine = create_engine(
                settings.DATABASE_URL,
                connect_args=connect_args,
                poolclass=StaticPool,
                echo=settings.DEBUG,
            )
        else:
            cls._engine = create_engine(
                settings.DATABASE_URL,
                connect_args=connect_args,
                echo=settings.DEBUG,
            )

        @event.listens_for(cls._engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """启用 SQLite 外键支持"""
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        logger.info(f"SQLite 数据库引擎创建成功: {settings.DATABASE_URL}")

    @classmethod
    def _create_postgres_engine(cls) -> None:
        """
        创建 PostgreSQL 数据库引擎
        配置连接池参数
        """
        cls._engine = create_engine(
            settings.DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
        logger.info("PostgreSQL 数据库引擎创建成功")

    @classmethod
    def get_session_factory(cls) -> sessionmaker:
        """
        获取会话工厂
        用于创建数据库会话

        Returns:
            SQLAlchemy sessionmaker 实例
        """
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
        """
        创建所有数据表
        在应用启动时调用
        """
        engine = cls.get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建完成")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖项：获取数据库会话
    自动处理会话的创建和关闭
    """
    session_factory = DatabaseConfig.get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
