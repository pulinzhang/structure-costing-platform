"""应用启动 / 关闭：目录、建表、种子、连接池。"""

import socket

from app.config import ensure_directories, settings
from app.database import AuxiliaryDatabaseConfig, DatabaseConfig
from app.utils.logging_config import get_logger

logger = get_logger("bootstrap.lifecycle")


def on_startup() -> None:
    ensure_directories()
    from app import models as _orm_models  # noqa: F401

    DatabaseConfig.create_tables()
    AuxiliaryDatabaseConfig.create_tables()
    _ensure_bom_node_part_number_index()
    _seed_if_empty()
    _log_startup()


def on_shutdown() -> None:
    DatabaseConfig.dispose()
    AuxiliaryDatabaseConfig.dispose()
    logger.info("应用正在关闭...")


def _ensure_bom_node_part_number_index() -> None:
    """现网 create_all 不补已有表索引。"""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    engine = DatabaseConfig.get_engine()
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_bom_node_part_number ON bom_nodes (part_number)"
                )
            )
        logger.info("已确保索引 ix_bom_node_part_number")
    except OperationalError:
        logger.exception("无法创建索引 ix_bom_node_part_number")


def _seed_if_empty() -> None:
    from app.services.masterdata.steel_grade_category import SteelGradeCategoryService
    from app.services.settings.users.user_service import UserService

    session_factory = DatabaseConfig.get_session_factory()
    db = session_factory()
    try:
        UserService().ensure_default_admin(db)
        SteelGradeCategoryService().ensure_seed_if_empty(db)
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
