"""系统设置业务逻辑。"""

from __future__ import annotations

from typing import Any


from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.config import settings as app_settings
from app.schemas.dto.settings_dto import SystemConfigUpdateDTO
from app.schemas.vo.settings_vo import ConfigVO
from app.schemas.vo.user_vo import UserVO
from app.repositories.settings.system.system_config_repository import SystemConfigRepository

DEFAULT_APP_NAME = "汽车冲压件自动核价平台"
DEFAULT_STEEL_DENSITY = Decimal("7.85")
DEFAULT_MATERIAL_LOSS_RATE = Decimal("0.003")  # 千分之 3
DEFAULT_SCRAP_RECOVERY_RATE = Decimal("0.97")  # 97%
APP_VERSION = "1.0.0"


class SettingsService:
    """系统配置：单例读写 + 核价用参数读取。"""

    def __init__(self) -> None:
        self.repository = SystemConfigRepository()

    def get_config(self, db: Session) -> ConfigVO:
        row = self.repository.get_singleton(db)
        if row is None:
            return ConfigVO(
                app_name=app_settings.APP_NAME or DEFAULT_APP_NAME,
                version=APP_VERSION,
                steel_density=float(DEFAULT_STEEL_DENSITY),
                material_loss_rate=float(DEFAULT_MATERIAL_LOSS_RATE),
                scrap_recovery_rate=float(DEFAULT_SCRAP_RECOVERY_RATE),
            )
        return ConfigVO(
            app_name=row.app_name or DEFAULT_APP_NAME,
            version=APP_VERSION,
            steel_density=self._normalize_density(row.steel_density),
            material_loss_rate=self._normalize_loss_rate(
                getattr(row, "material_loss_rate", None)
            ),
            scrap_recovery_rate=self._normalize_recovery_rate(
                getattr(row, "scrap_recovery_rate", None)
            ),
        )

    def update_config(
        self,
        db: Session,
        dto: SystemConfigUpdateDTO,
        current_user: UserVO,
    ) -> ConfigVO:
        app_name = dto.app_name.strip() or DEFAULT_APP_NAME
        payload_fields = {
            "app_name": app_name,
            "steel_density": Decimal(str(dto.steel_density)),
            "material_loss_rate": Decimal(str(dto.material_loss_rate)),
            "scrap_recovery_rate": Decimal(str(dto.scrap_recovery_rate)),
        }
        row = self.repository.get_singleton(db)
        if row is None:
            self.repository.create_singleton(
                db,
                {**payload_fields, **audit_create(current_user)},
            )
        else:
            self.repository.update_singleton(
                db,
                row,
                {**payload_fields, **audit_update(current_user)},
            )
        db.commit()
        return self.get_config(db)

    def get_steel_density(self, db: Session) -> Decimal:
        """核价用：读系统配置密度，无效或缺失则回退 7.85。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_STEEL_DENSITY
        return Decimal(str(self._normalize_density(row.steel_density)))

    def get_material_loss_rate(self, db: Session) -> Decimal:
        """核价用：读冲压材料损耗率，无效或缺失则回退 0.003（千分之3）。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_MATERIAL_LOSS_RATE
        return Decimal(
            str(
                self._normalize_loss_rate(
                    getattr(row, "material_loss_rate", None)
                )
            )
        )

    def get_scrap_recovery_rate(self, db: Session) -> Decimal:
        """核价用：读废料回收率，无效或缺失则回退 0.97。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_SCRAP_RECOVERY_RATE
        return Decimal(
            str(
                self._normalize_recovery_rate(
                    getattr(row, "scrap_recovery_rate", None)
                )
            )
        )

    @staticmethod
    def _normalize_density(value: Any) -> float:
        try:
            density = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return float(DEFAULT_STEEL_DENSITY)
        if density <= 0:
            return float(DEFAULT_STEEL_DENSITY)
        return float(density)

    @staticmethod
    def _normalize_loss_rate(value: Any) -> float:
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return float(DEFAULT_MATERIAL_LOSS_RATE)
        if rate < 0:
            return float(DEFAULT_MATERIAL_LOSS_RATE)
        return float(rate)

    @staticmethod
    def _normalize_recovery_rate(value: Any) -> float:
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return float(DEFAULT_SCRAP_RECOVERY_RATE)
        if rate <= 0 or rate > 1:
            return float(DEFAULT_SCRAP_RECOVERY_RATE)
        return float(rate)
