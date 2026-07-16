"""
日志配置模块
统一的日志配置，支持控制台和文件输出
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from app.config import settings


class LoggerConfig:
    """
    日志配置类
    提供统一的日志配置和管理
    """

    _loggers = {}
    _configured = False

    @classmethod
    def configure(cls) -> None:
        """
        配置全局日志
        只需调用一次，在应用启动时执行
        """
        if cls._configured:
            return

        # 确保日志目录存在
        settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

        # 配置根日志器
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

        # 清除现有处理器
        root_logger.handlers.clear()

        # 添加控制台处理器
        console_handler = cls._create_console_handler()
        root_logger.addHandler(console_handler)

        # 添加文件处理器
        file_handler = cls._create_file_handler()
        root_logger.addHandler(file_handler)

        cls._configured = True

        logging.info(f"日志系统初始化完成，日志级别: {settings.LOG_LEVEL}")

    @staticmethod
    def _create_console_handler() -> logging.Handler:
        """创建控制台处理器"""
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        return handler

    @staticmethod
    def _create_file_handler() -> logging.Handler:
        """创建文件处理器"""
        log_file = settings.LOG_DIR / "app.log"
        handler = RotatingFileHandler(
            filename=str(log_file),
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8"
        )
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        return handler

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        获取指定名称的日志器
        使用分层命名: router.xxx, service.xxx, repository.xxx

        Args:
            name: 日志器名称，如 'router.dashboard', 'service.costing'

        Returns:
            logging.Logger 实例
        """
        if not cls._configured:
            cls.configure()

        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger

        return cls._loggers[name]


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器的便捷函数

    Args:
        name: 日志器名称，建议格式: '模块类型.功能名'
              例如: 'router.dashboard', 'service.costing', 'parser.excel'

    Returns:
        logging.Logger 实例
    """
    return LoggerConfig.get_logger(name)


def log_request(logger: logging.Logger, method: str, path: str) -> None:
    """记录 HTTP 请求"""
    logger.info(f"请求: {method} {path}")


def log_response(logger: logging.Logger, method: str, path: str, status: int, duration_ms: float) -> None:
    """记录 HTTP 响应"""
    logger.info(f"响应: {method} {path} - 状态:{status} - 耗时:{duration_ms:.2f}ms")


def log_error(logger: logging.Logger, error: Exception, context: Optional[str] = None) -> None:
    """记录错误日志"""
    if context:
        logger.error(f"{context} - 错误: {type(error).__name__}: {str(error)}", exc_info=True)
    else:
        logger.error(f"错误: {type(error).__name__}: {str(error)}", exc_info=True)


def log_business_operation(logger: logging.Logger, operation: str, details: dict) -> None:
    """记录业务操作日志"""
    detail_str = " | ".join([f"{k}={v}" for k, v in details.items()])
    logger.info(f"业务操作: {operation} | {detail_str}")
