"""
日志配置模块
统一的日志配置，支持控制台和文件输出
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler

from app.config import settings


class LoggerConfig:
    """
    日志配置类
    提供统一的日志配置和管理
    """

    _configured = False

    @classmethod
    def configure(cls, force: bool = False) -> None:
        """
        配置全局日志
        只需调用一次，在应用启动时执行

        Args:
            force: 是否强制重新配置
        """
        if cls._configured and not force:
            return

        # 确保日志目录存在
        settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

        # 配置根日志器
        root_logger = logging.getLogger()
        
        # 只在还没有配置时设置
        if not cls._configured:
            # 重要：清除所有现有的处理器
            root_logger.handlers.clear()
            
            # 设置日志级别
            level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
            root_logger.setLevel(level)
            
            # 添加控制台处理器
            console_handler = cls._create_console_handler()
            console_handler.setLevel(level)
            root_logger.addHandler(console_handler)

        # 添加文件处理器（总是添加，不检查是否已存在）
        file_handler = cls._create_file_handler()
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

        cls._configured = True

        logging.info(f"日志系统初始化完成，日志级别: {settings.LOG_LEVEL}")

    @staticmethod
    def _create_console_handler() -> logging.Handler:
        """创建控制台处理器"""
        # 写入 stderr 而不是 stdout，避免被 uvicorn 捕获后重定向
        handler = logging.StreamHandler(sys.stderr)
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
        
        # 验证目录可写
        import os
        if not os.access(settings.LOG_DIR, os.W_OK):
            print(f"[FATAL] 日志目录不可写: {settings.LOG_DIR}", file=sys.stderr)
        
        # 自定义 Handler，确保每次写入后立即刷新到磁盘
        class SafeRotatingFileHandler(RotatingFileHandler):
            def emit(self, record):
                try:
                    super().emit(record)
                    self.flush()
                except Exception as e:
                    pass  # 静默忽略日志写入错误，避免干扰主流程
        
        try:
            handler = SafeRotatingFileHandler(
                filename=str(log_file),
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[FATAL] 无法创建文件处理器: {e}", file=sys.stderr)
            raise
        
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
        # 每次都确保配置已初始化
        if not cls._configured:
            cls.configure()

        # 每次都获取新的 logger 实例，避免缓存导致的问题
        logger = logging.getLogger(name)
        return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取日志器的便捷函数

    Args:
        name: 日志器名称，建议格式: '模块类型.功能名'
              例如: 'router.dashboard', 'service.costing', 'parser.excel'

    Returns:
        logging.Logger 实例
    """
    # 确保配置已初始化
    if not LoggerConfig._configured:
        LoggerConfig.configure(force=True)

    # 获取日志器
    logger = logging.getLogger(name)
    
    # 确保日志器的级别与根日志器一致，避免子 logger 被设置为 NOTSET 导致不输出
    root_logger = logging.getLogger()
    if logger.level == 0:  # 0 表示 NOTSET
        logger.setLevel(root_logger.level)
    
    return logger


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
