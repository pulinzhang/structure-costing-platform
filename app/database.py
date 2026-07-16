"""
数据库配置模块
提供 SQLAlchemy 数据库连接和会话管理
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool

from app.config import settings


logger = logging.getLogger(__name__)

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

    @classmethod
    def drop_tables(cls) -> None:
        """
        删除所有数据表
        仅在测试或数据重置时使用
        """
        engine = cls.get_engine()
        Base.metadata.drop_all(bind=engine)
        logger.warning("数据库表已删除")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖项：获取数据库会话
    自动处理会话的创建和关闭

    Args:
        Generator[Session, None, None]: 数据库会话生成器

    Yields:
        Session: 数据库会话实例

    Example:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    session_factory = DatabaseConfig.get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    上下文管理器：获取数据库会话
    适用于非 FastAPI 路由的场景

    Yields:
        Session: 数据库会话实例

    Example:
        with get_db_session() as session:
            result = session.query(Item).all()
    """
    session_factory = DatabaseConfig.get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class UnitOfWork:
    """
    工作单元模式
    用于管理复杂业务逻辑中的数据库事务
    """

    def __init__(self):
        self.session: Session = None

    def __enter__(self) -> "UnitOfWork":
        session_factory = DatabaseConfig.get_session_factory()
        self.session = session_factory()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            self.session.rollback()
            logger.error(f"事务回滚: {exc_val}")
            return False

        self.session.commit()
        return True

    def close(self) -> None:
        """关闭会话"""
        if self.session:
            self.session.close()
