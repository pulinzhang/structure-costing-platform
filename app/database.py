"""
数据库配置模块
提供 SQLAlchemy 数据库连接和会话管理

主业务库（DatabaseConfig）与辅助库（AuxiliaryDatabaseConfig）隔离：
无 Redis 时，辅助库承载会话 Token、异步任务进度等短生命周期数据，
SQLite 使用独立文件，写入不受主业务长事务锁影响。
"""

from pathlib import Path
from typing import Generator
from urllib.parse import unquote, urlparse

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.utils.logging_config import get_logger


logger = get_logger("database")

Base = declarative_base()
AuxiliaryBase = declarative_base()

# 仅属于辅助库的表；若误出现在主库则启动时删除
_AUXILIARY_ONLY_TABLES = ("user_tokens", "async_tasks")


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


def _sqlite_path_from_url(database_url: str) -> Path | None:
    """从 sqlite URL 解析本地文件路径；内存库返回 None。"""
    if "sqlite" not in database_url:
        return None
    if ":memory:" in database_url or "mode=memory" in database_url:
        return None
    parsed = urlparse(database_url)
    raw = unquote(parsed.path or "")
    # Windows: sqlite:///D:/foo.db → /D:/foo.db
    if raw.startswith("/") and len(raw) > 2 and raw[2] == ":":
        raw = raw[1:]
    if not raw:
        return None
    return Path(raw)


def _migrate_legacy_async_tasks_db(target_url: str) -> None:
    """兼容旧文件名 async_tasks.db → auxiliary.db（仅文件不存在时迁移）。"""
    target = _sqlite_path_from_url(target_url)
    if target is None:
        return
    if target.exists():
        return
    legacy = target.with_name("async_tasks.db")
    if not legacy.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    legacy.rename(target)
    # WAL 伴随文件一并迁移（若存在）
    for suffix in ("-wal", "-shm"):
        legacy_side = Path(str(legacy) + suffix)
        if legacy_side.exists():
            legacy_side.rename(Path(str(target) + suffix))
    logger.info("已迁移辅助库文件: %s → %s", legacy.name, target.name)


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
    def _drop_misplaced_auxiliary_tables(cls, engine) -> None:
        """主库不应存在辅助表；历史 create_all 误建时启动清理。"""
        from sqlalchemy import inspect, text

        try:
            existing = set(inspect(engine).get_table_names())
        except Exception:
            logger.exception("检查主库误建表失败")
            return

        for table_name in _AUXILIARY_ONLY_TABLES:
            if table_name not in existing:
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
                logger.warning("已从主业务库移除误建表: %s（应仅存在于辅助库）", table_name)
            except Exception:
                logger.exception("删除主库误建表失败: %s", table_name)

    @classmethod
    def create_tables(cls) -> None:
        engine = cls.get_engine()
        cls._drop_misplaced_auxiliary_tables(engine)
        Base.metadata.create_all(bind=engine)
        logger.info("主业务库表创建完成")


class AuxiliaryDatabaseConfig:
    """
    辅助数据库配置（无 Redis 时的旁路存储）。

    承载：异步任务进度、登录 Token 等短生命周期数据。
    """

    _engine = None
    _session_factory = None

    @classmethod
    def get_engine(cls):
        if cls._engine is None:
            _migrate_legacy_async_tasks_db(settings.AUXILIARY_DATABASE_URL)
            cls._engine = _create_engine_for_url(
                settings.AUXILIARY_DATABASE_URL,
                label="辅助库",
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
        import app.models.user_token  # noqa: F401

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
