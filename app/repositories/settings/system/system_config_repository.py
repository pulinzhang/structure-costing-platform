"""系统配置 Repository — 仅做单例行读写。"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.settings import SystemConfig
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.settings_dto import SystemConfigPatch, SystemConfigWrite

SINGLETON_ID = 1
_FINISHED_RATES_COLUMN = "calculate_finished_rates"
_RETIRED_RATE_COLUMNS = (
    "finished_finance_rate",
    "finished_management_rate",
    "finished_warehouse_packaging_rate",
    "finished_scrap_rate",
    "finished_pretax_profit_rate",
)


class SystemConfigRepository:
    """系统配置数据访问。"""

    def ensure_calculate_finished_rates_column(self, db: Session) -> bool:
        """旧库补「是否计算成品费率」。已有列则不动。"""
        bind = db.get_bind()
        inspector = inspect(bind)
        table = SystemConfig.__tablename__
        if not inspector.has_table(table):
            return False
        present = {column["name"] for column in inspector.get_columns(table)}
        if _FINISHED_RATES_COLUMN in present:
            return False
        if bind.dialect.name == "postgresql":
            ddl = (
                f"ALTER TABLE {table} ADD COLUMN {_FINISHED_RATES_COLUMN} "
                "BOOLEAN NOT NULL DEFAULT TRUE"
            )
        else:
            ddl = (
                f"ALTER TABLE {table} ADD COLUMN {_FINISHED_RATES_COLUMN} "
                "BOOLEAN NOT NULL DEFAULT 1"
            )
        db.execute(text(ddl))
        return True

    def drop_retired_finished_rate_columns(self, db: Session) -> bool:
        """设置里已经不读这五列。旧库还在时删掉，避免和计费管理各存一套费率。"""
        bind = db.get_bind()
        inspector = inspect(bind)
        table = SystemConfig.__tablename__
        if not inspector.has_table(table):
            return False
        present = {column["name"] for column in inspector.get_columns(table)}
        retired = [name for name in _RETIRED_RATE_COLUMNS if name in present]
        if not retired:
            return False
        for index in inspector.get_indexes(table):
            index_name = index.get("name")
            column_names = index.get("column_names") or []
            if index_name and any(name in column_names for name in retired):
                db.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))
        for name in retired:
            db.execute(text(f"ALTER TABLE {table} DROP COLUMN {name}"))
        return True

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
