"""系统配置 Repository — 仅做单例行读写。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.settings import SystemConfig
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.settings_dto import SystemConfigPatch, SystemConfigWrite

SINGLETON_ID = 1


class SystemConfigRepository:
    """系统配置数据访问。"""

    def get_singleton(self, db: Session) -> SystemConfig | None:
        return db.query(SystemConfig).filter(SystemConfig.id == SINGLETON_ID).first()

    def create_singleton(self, db: Session, data: SystemConfigWrite) -> SystemConfig:
        row = model_from_payload(SystemConfig, data)
        row.id = SINGLETON_ID
        db.add(row)
        db.flush()
        return row

    def update_singleton(
        self,
        db: Session,
        row: SystemConfig,
        data: SystemConfigPatch,
    ) -> SystemConfig:
        apply_payload_fields(row, data)
        db.flush()
        return row
