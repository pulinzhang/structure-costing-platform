"""系统配置 Repository — 仅做单例行读写。"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.system_config import SystemConfig

SINGLETON_ID = 1


class SystemConfigRepository:
    """系统配置数据访问。"""

    def get_singleton(self, db: Session) -> SystemConfig | None:
        return (
            db.query(SystemConfig)
            .filter(SystemConfig.id == SINGLETON_ID)
            .first()
        )

    def create_singleton(self, db: Session, data: dict[str, Any]) -> SystemConfig:
        row = SystemConfig(id=SINGLETON_ID, **data)
        db.add(row)
        db.flush()
        return row

    def update_singleton(
        self,
        db: Session,
        row: SystemConfig,
        data: dict[str, Any],
    ) -> SystemConfig:
        for key, value in data.items():
            setattr(row, key, value)
        db.flush()
        return row
