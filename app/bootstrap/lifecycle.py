"""应用启动 / 关闭：目录、建表、种子、连接池。"""

import socket

from app.config import ensure_directories, settings
from app.database import AuxiliaryDatabaseConfig, DatabaseConfig
from app.utils.logging_config import attach_health_probe_access_filter, get_logger

logger = get_logger("bootstrap.lifecycle")


def on_startup() -> None:
    attach_health_probe_access_filter()
    ensure_directories()
    from app import models as _orm_models  # noqa: F401

    DatabaseConfig.create_tables()
    AuxiliaryDatabaseConfig.create_tables()
    _seed_if_empty()
    _log_startup()


def on_shutdown() -> None:
    DatabaseConfig.dispose()
    AuxiliaryDatabaseConfig.dispose()
    logger.info("应用正在关闭...")


def _seed_if_empty() -> None:
    from app.services.masterdata.steel_grade_category.service import (
        SteelGradeCategoryService,
    )
    from app.services.masterdata.steel_mill.service import SteelMillService
    from app.services.settings.schema_comment.seed import ensure_schema_reference_seed
    from app.services.settings.users.service import UserService

    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        UserService().ensure_default_admin(db)
        SteelGradeCategoryService().ensure_seed_if_empty(db)
        SteelMillService().ensure_seed_if_empty(db)
        ensure_schema_reference_seed(db)
    finally:
        db.close()


def _log_startup() -> None:
    logger.info("=" * 50)
    logger.info("%s 正在启动...", settings.APP_NAME)
    logger.info("版本: %s", settings.APP_VERSION)
    logger.info("环境: %s", settings.ENV)
    logger.info("=" * 50)
    logger.info("API 服务启动完成")
    display_host = "127.0.0.1" if settings.HOST in {"0.0.0.0", "::"} else settings.HOST
    logger.info("本机访问: http://%s:%s", display_host, settings.PORT)
    if settings.HOST in {"0.0.0.0", "::"}:
        for lan_ip in _local_ipv4_addresses():
            logger.info("局域网访问: http://%s:%s", lan_ip, settings.PORT)
    logger.info("前端静态页面: 使用 Live Server 打开 static/index.html")


def _local_ipv4_addresses() -> list[str]:
    addresses: list[str] = []
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM):
            ip = info[4][0]
            if not isinstance(ip, str) or ip.startswith("127.") or ip in addresses:
                continue
            addresses.append(ip)
    except OSError:
        pass
    if not addresses:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                ip = sock.getsockname()[0]
                if not ip.startswith("127."):
                    addresses.append(ip)
        except OSError:
            pass
    return addresses
