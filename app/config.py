"""
配置文件 - 应用配置管理
统一的配置入口，支持多环境配置
"""

import os
from pathlib import Path
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings
# 项目根目录 (app/config.py -> app/ -> 项目根目录)

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# 获取环境变量，默认为 development
ENV: str = os.getenv("APP_ENV", "development")

# 兼容旧环境变量 DEBUG
_IS_DEBUG_ALIAS = AliasChoices("IS_DEBUG", "DEBUG")


class Settings(BaseSettings):
    """
    应用设置
    使用 Pydantic Settings 进行配置管理
    """

    # 应用基本信息
    APP_NAME: str = "汽车冲压件自动核价平台"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Stamping Costing Platform"
    IS_DEBUG: bool = Field(default=True, validation_alias=_IS_DEBUG_ALIAS)
    ENV: str = "development"

    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 数据库配置
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/stamping_costing.db"
    # 辅助库（无 Redis）：Token 会话、异步任务进度等，与主库隔离
    AUXILIARY_DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/auxiliary.db"
    # 时区真相在 app.common.timezone；此处仅作配置声明/文档对齐
    TIMEZONE: str = "Asia/Shanghai"

    # 密码摘要盐（MD5(salt + password)）；生产环境务必通过环境变量覆盖
    PASSWORD_SALT: str = "chery-stamping-costing-2024"

    # 登录会话：无业务请求超时（分钟）。未配置时默认 15；心跳 /api/auth/touch 不续期
    TOKEN_IDLE_MINUTES: int = Field(default=15, ge=1, le=1440)

    @field_validator("TOKEN_IDLE_MINUTES", mode="before")
    @classmethod
    def _default_token_idle_minutes(cls, value: object) -> object:
        if value is None:
            return 15
        if isinstance(value, str) and not value.strip():
            return 15
        return value

    # 上传配置
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: set[str] = {".xlsx", ".xls", ".csv"}

    # 日志配置
    LOG_DIR: Path = BASE_DIR / "logs"
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # CORS 配置
    CORS_ORIGINS: list[str] = ["*"]

    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # LLM（OpenAI 兼容；仅 llm client 使用）
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "deepseek-chat"
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_TIMEOUT_SECONDS: int = 90
    LLM_IDEMPOTENCY_TTL_MINUTES: int = 5
    LLM_MAX_CONCURRENT_TASKS_PER_USER: int = 2

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"
        populate_by_name = True


# 根据环境调整配置
class DevelopmentSettings(Settings):
    """开发环境配置"""

    IS_DEBUG: bool = Field(default=True, validation_alias=_IS_DEBUG_ALIAS)
    LOG_LEVEL: str = "DEBUG"


class ProductionSettings(Settings):
    """生产环境配置"""

    IS_DEBUG: bool = Field(default=False, validation_alias=_IS_DEBUG_ALIAS)
    LOG_LEVEL: str = "WARNING"
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
    ]  # 生产环境白名单


class TestSettings(Settings):
    """测试环境配置"""

    IS_DEBUG: bool = Field(default=True, validation_alias=_IS_DEBUG_ALIAS)
    DATABASE_URL: str = "sqlite:///:memory:"
    AUXILIARY_DATABASE_URL: str = "sqlite:///:memory:"


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
