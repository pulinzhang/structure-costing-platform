"""业务统一时区：东八区（Asia/Shanghai）。

约定：
- 库内 DateTime 一律存「东八区墙钟」的 naive datetime（不带 tzinfo）
- 禁止依赖 SQLite CURRENT_TIMESTAMP（其为 UTC）
- 写入统一用 now()；引擎连接时声明 Asia/Shanghai（PostgreSQL）
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

CHINA_TZ_NAME = "Asia/Shanghai"
CHINA_TZ = ZoneInfo(CHINA_TZ_NAME)


def now() -> datetime:
    """当前东八区墙钟时间（naive，用于入库与业务比较）。"""
    return datetime.now(CHINA_TZ).replace(tzinfo=None)


def datetime_to_iso(value: datetime | date | str | None) -> str | None:
    """VO / API JSON 的 datetime / date：必须 isoformat（如 2026-08-25T10:42:00 / 2026-08-25）。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
