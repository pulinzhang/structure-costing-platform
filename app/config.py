"""
配置文件 - 应用配置管理
统一的配置入口，支持多环境配置
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings


# 项目根目录
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

# 获取环境变量，默认为 development
ENV: str = os.getenv("APP_ENV", "development")


class Settings(BaseSettings):
    """
    应用设置
    使用 Pydantic Settings 进行配置管理
    """

    # 应用基本信息
    APP_NAME: str = "汽车冲压件自动核价平台"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Stamping Costing Platform"
    DEBUG: bool = True

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库配置
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/stamping_costing.db"

    # 上传配置
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set = {".xlsx", ".xls", ".csv"}

    # 日志配置
    LOG_DIR: Path = BASE_DIR / "logs"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # CORS 配置
    CORS_ORIGINS: list = ["*"]

    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True


# 根据环境调整配置
class DevelopmentSettings(Settings):
    """开发环境配置"""
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"


class ProductionSettings(Settings):
    """生产环境配置"""
    DEBUG: bool = False
    LOG_LEVEL: str = "WARNING"


class TestSettings(Settings):
    """测试环境配置"""
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///:memory:"


# 环境配置映射
SETTINGS_MAP = {
    "development": DevelopmentSettings(),
    "production": ProductionSettings(),
    "test": TestSettings(),
}


def get_settings() -> Settings:
    """
    获取当前环境的配置
    根据 APP_ENV 环境变量加载对应配置
    """
    return SETTINGS_MAP.get(ENV, DevelopmentSettings())


# 全局配置实例
settings = get_settings()


def ensure_directories() -> None:
    """
    确保必要的目录存在
    在应用启动时调用
    """
    directories = [
        settings.UPLOAD_DIR,
        settings.LOG_DIR,
        BASE_DIR / "data",
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
