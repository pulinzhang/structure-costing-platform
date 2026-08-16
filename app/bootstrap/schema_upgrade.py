"""
数据库 Schema 启动升级（生产与开发共用）。

设计要点：
- 本项目未使用 Alembic；升级逻辑集中在此入口。
- 多 Worker 时各进程都会跑 lifespan，必须用文件锁串行化，避免并发 ALTER/DROP。
- 推荐生产入口 ``run_prod.py``：先单独跑一遍升级，失败则不启动服务；
  lifespan 内再次调用是幂等兜底（锁 + 可重复执行）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import BinaryIO

from app.config import BASE_DIR, ensure_directories
from app.utils.logging_config import get_logger

logger = get_logger("schema_upgrade")

_LOCK_PATH = BASE_DIR / "data" / ".schema_upgrade.lock"


class _SchemaFileLock:
    """跨进程互斥（Windows msvcrt / Unix fcntl）。"""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._handle: BinaryIO | None = None

    def __enter__(self) -> "_SchemaFileLock":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = open(self._path, "a+b")
        assert self._handle is not None
        self._handle.seek(0)
        if self._handle.read(1) == b"":
            self._handle.write(b"\0")
            self._handle.flush()
        self._handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *args: object) -> None:
        if self._handle is None:
            return
        try:
            self._handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None


def run_schema_upgrade(*, ensure_admin: bool = True) -> None:
    """
    执行目录保障、Model 对齐、破坏性表迁移、建表，以及可选的默认管理员。

    失败时抛出异常；由 ``run_prod.py`` 捕获后以非零退出码阻断启动。
    """
    if os.getenv("SKIP_SCHEMA_UPGRADE", "").strip().lower() in {"1", "true", "yes"}:
        logger.warning("[schema_upgrade] SKIP_SCHEMA_UPGRADE 已设置，跳过升级")
        return

    with _SchemaFileLock(_LOCK_PATH):
        logger.info("[schema_upgrade] 获得锁，开始 Schema 升级...")
        ensure_directories()

        # 注册全部 Model，供 metadata / 自动 ADD COLUMN 扫描
        import app.models  # noqa: F401

        from app.database import AuxiliaryDatabaseConfig, DatabaseConfig
        from app.utils.db_migration import run_auto_migration
        from app.utils.scrap_price_location_migration import (
            run_scrap_price_location_migration,
        )
        from app.utils.steel_price_key_migration import run_steel_price_key_migration

        # 顺序：先补列 → 再处理无法 ADD 的破坏性迁移 → create_all
        run_auto_migration()
        run_steel_price_key_migration(DatabaseConfig.get_engine())
        run_scrap_price_location_migration(DatabaseConfig.get_engine())
        DatabaseConfig.create_tables()
        AuxiliaryDatabaseConfig.create_tables()

        if ensure_admin:
            from app.services.settings.users.user_service import UserService

            session_factory = DatabaseConfig.get_session_factory()
            db = session_factory()
            try:
                UserService().ensure_default_admin(db)
            finally:
                db.close()

        logger.info("[schema_upgrade] Schema 升级完成")


def main() -> None:
    """CLI：``python -m app.bootstrap.schema_upgrade``"""
    try:
        run_schema_upgrade(ensure_admin=True)
    except Exception:
        logger.exception("[schema_upgrade] 失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
