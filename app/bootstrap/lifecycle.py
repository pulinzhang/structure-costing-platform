"""应用启动 / 关闭：目录、建表、种子、连接池。"""

import os
import socket
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import cast

from app.config import ensure_directories, settings
from app.database import AuxiliaryDatabaseConfig, DatabaseConfig
from app.utils.logging_config import attach_health_probe_access_filter, get_logger

logger = get_logger("bootstrap.lifecycle")
_NS_PER_SECOND = 1_000_000_000
# Windows FILETIME 从 1601-01-01 起算，Unix 从 1970-01-01 起算。
_WINDOWS_EPOCH_OFFSET_NS = 11_644_473_600 * _NS_PER_SECOND


def on_startup() -> None:
    phase_started_ns = time.perf_counter_ns()
    attach_health_probe_access_filter()
    ensure_directories()
    from app import models as _orm_models  # noqa: F401

    DatabaseConfig.create_tables()
    AuxiliaryDatabaseConfig.create_tables()
    _seed_if_empty()
    _log_startup(phase_started_ns)


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


def _log_startup(phase_started_ns: int) -> None:
    logger.info("=" * 50)
    logger.info("%s 正在启动...", settings.APP_NAME)
    logger.info("版本: %s", settings.APP_VERSION)
    logger.info("环境: %s", settings.ENV)
    logger.info("=" * 50)
    logger.info("API 服务启动完成")
    logger.info("启动耗时: %s 秒", _format_elapsed_seconds(_startup_elapsed_ns(phase_started_ns)))
    display_host = "127.0.0.1" if settings.HOST in {"0.0.0.0", "::"} else settings.HOST
    logger.info("本机访问: http://%s:%s", display_host, settings.PORT)
    if settings.HOST in {"0.0.0.0", "::"}:
        for lan_ip in _local_ipv4_addresses():
            logger.info("局域网访问: http://%s:%s", lan_ip, settings.PORT)
    logger.info("前端静态页面: 使用 Live Server 打开 static/index.html")


def _format_elapsed_seconds(elapsed_ns: int) -> str:
    elapsed_ms = max(0, elapsed_ns) // 1_000_000
    return f"{elapsed_ms // 1000}.{(elapsed_ms % 1000) // 10:02d}"


def _startup_elapsed_ns(phase_started_ns: int) -> int:
    """进程创建到当前的纳秒。读不到创建时间时只计 on_startup 这一段。"""
    started_ns = _process_start_unix_ns()
    if started_ns is None:
        return max(0, time.perf_counter_ns() - phase_started_ns)
    return max(0, time.time_ns() - started_ns)


def _process_start_unix_ns() -> int | None:
    platform: str = sys.platform
    if platform == "linux":
        return _linux_process_start_unix_ns()
    if platform == "win32":
        return _windows_process_start_unix_ns()
    return None


def _linux_process_start_unix_ns() -> int | None:
    # os.sysconf 只出现在 Unix 的类型声明里，Windows 上直接点名过不了检查。
    sysconf = getattr(os, "sysconf", None)
    if not callable(sysconf):
        return None
    try:
        clock_ticks = int(cast(Callable[[str], int], sysconf)("SC_CLK_TCK"))
        stat_text = Path("/proc/self/stat").read_text(encoding="ascii")
        uptime_text = Path("/proc/uptime").read_text(encoding="ascii")
        uptime_ns = _decimal_seconds_to_ns(uptime_text.split()[0])
    except (OSError, ValueError, IndexError):
        return None
    return _unix_ns_from_proc_stat(
        stat_text,
        uptime_ns=uptime_ns,
        now_ns=time.time_ns(),
        clock_ticks=clock_ticks,
    )


def _decimal_seconds_to_ns(text: str) -> int:
    whole_text, dot, frac_text = text.strip().partition(".")
    if not whole_text or (dot and not frac_text):
        raise ValueError(text)
    frac_ns = int((frac_text + "000000000")[:9]) if frac_text else 0
    return int(whole_text) * _NS_PER_SECOND + frac_ns


def _unix_ns_from_proc_stat(
    stat_text: str,
    *,
    uptime_ns: int,
    now_ns: int,
    clock_ticks: int,
) -> int | None:
    # 第 22 项是开机后的时钟 tick。comm 可含空格和括号，从最后一个 ) 之后数。
    end = stat_text.rfind(")")
    if end < 0 or clock_ticks <= 0:
        return None
    fields = stat_text[end + 2 :].split()
    if len(fields) < 20:
        return None
    try:
        start_ticks = int(fields[19])
    except ValueError:
        return None
    start_ns = (start_ticks * _NS_PER_SECOND + clock_ticks // 2) // clock_ticks
    return now_ns - (uptime_ns - start_ns)


def _windows_process_start_unix_ns() -> int | None:
    import ctypes

    # WinDLL 只出现在 Windows 的类型声明里，Linux 上直接点名过不了检查。
    windll = getattr(ctypes, "WinDLL", None)
    if not callable(windll):
        return None

    class FileTime(ctypes.Structure):
        _fields_ = (("low", ctypes.c_uint32), ("high", ctypes.c_uint32))

    kernel32 = cast(Callable[..., ctypes.CDLL], windll)("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.GetProcessTimes.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
        ctypes.POINTER(FileTime),
    ]
    kernel32.GetProcessTimes.restype = ctypes.c_int

    created = FileTime()
    unused = FileTime()
    ok = kernel32.GetProcessTimes(
        kernel32.GetCurrentProcess(),
        ctypes.byref(created),
        ctypes.byref(unused),
        ctypes.byref(unused),
        ctypes.byref(unused),
    )
    if not ok:
        return None
    ticks = (int(created.high) << 32) | int(created.low)
    return ticks * 100 - _WINDOWS_EPOCH_OFFSET_NS


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
