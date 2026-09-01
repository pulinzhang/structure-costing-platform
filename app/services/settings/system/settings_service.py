"""系统设置业务逻辑。"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from app.common.audit import audit_create, audit_update
from app.common.money import Q4, Q6, quantize_money
from app.config import settings as app_settings
from app.repositories.settings.system.system_config_repository import SystemConfigRepository
from app.schemas.dto.settings_dto import (
    SystemConfigPatch,
    SystemConfigUpdateDTO,
    SystemConfigWrite,
)
from app.schemas.vo.settings_vo import ConfigVO
from app.schemas.vo.user_vo import UserVO

DEFAULT_APP_NAME = "汽车冲压件自动核价平台"
DEFAULT_STEEL_DENSITY = Decimal("7.85")
DEFAULT_MATERIAL_LOSS_RATE = Decimal("0.003")  # 千分之 3
DEFAULT_SCRAP_RECOVERY_RATE = Decimal("0.97")  # 97%
DEFAULT_FINISHED_FINANCE_RATE = Decimal("0.02")  # 2%
DEFAULT_FINISHED_MANAGEMENT_RATE = Decimal("0.02")  # 2%
DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE = Decimal("0.01")  # 1%
DEFAULT_FINISHED_SCRAP_RATE = Decimal("0.003")  # 千分之 3
DEFAULT_FINISHED_PRETAX_PROFIT_RATE = Decimal("0.02")  # 2%
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
                steel_density=DEFAULT_STEEL_DENSITY,
                material_loss_rate=DEFAULT_MATERIAL_LOSS_RATE,
                scrap_recovery_rate=DEFAULT_SCRAP_RECOVERY_RATE,
                finished_finance_rate=DEFAULT_FINISHED_FINANCE_RATE,
                finished_management_rate=DEFAULT_FINISHED_MANAGEMENT_RATE,
                finished_warehouse_packaging_rate=DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE,
                finished_scrap_rate=DEFAULT_FINISHED_SCRAP_RATE,
                finished_pretax_profit_rate=DEFAULT_FINISHED_PRETAX_PROFIT_RATE,
            )
        return ConfigVO(
            app_name=row.app_name or DEFAULT_APP_NAME,
            version=APP_VERSION,
            steel_density=self._normalize_density(row.steel_density),
            material_loss_rate=self._normalize_loss_rate(getattr(row, "material_loss_rate", None)),
            scrap_recovery_rate=self._normalize_recovery_rate(
                getattr(row, "scrap_recovery_rate", None)
            ),
            finished_finance_rate=self._normalize_percent_rate(
                getattr(row, "finished_finance_rate", None),
                DEFAULT_FINISHED_FINANCE_RATE,
            ),
            finished_management_rate=self._normalize_percent_rate(
                getattr(row, "finished_management_rate", None),
                DEFAULT_FINISHED_MANAGEMENT_RATE,
            ),
            finished_warehouse_packaging_rate=self._normalize_percent_rate(
                getattr(row, "finished_warehouse_packaging_rate", None),
                DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE,
            ),
            finished_scrap_rate=self._normalize_permille_rate(
                getattr(row, "finished_scrap_rate", None),
                DEFAULT_FINISHED_SCRAP_RATE,
            ),
            finished_pretax_profit_rate=self._normalize_percent_rate(
                getattr(row, "finished_pretax_profit_rate", None),
                DEFAULT_FINISHED_PRETAX_PROFIT_RATE,
            ),
        )

    def update_config(
        self,
        db: Session,
        dto: SystemConfigUpdateDTO,
        current_user: UserVO,
    ) -> ConfigVO:
        app_name = dto.app_name.strip() or DEFAULT_APP_NAME
        audit = audit_create(current_user)
        steel_density = quantize_money(dto.steel_density, Q4)
        material_loss_rate = quantize_money(dto.material_loss_rate, Q6)
        scrap_recovery_rate = quantize_money(dto.scrap_recovery_rate, Q6)
        finished_finance_rate = quantize_money(dto.finished_finance_rate, Q6)
        finished_management_rate = quantize_money(dto.finished_management_rate, Q6)
        finished_warehouse_packaging_rate = quantize_money(
            dto.finished_warehouse_packaging_rate, Q6
        )
        finished_scrap_rate = quantize_money(dto.finished_scrap_rate, Q6)
        finished_pretax_profit_rate = quantize_money(dto.finished_pretax_profit_rate, Q6)
        row = self.repository.get_singleton(db)
        if row is None:
            self.repository.create_singleton(
                db,
                SystemConfigWrite(
                    app_name=app_name,
                    steel_density=steel_density,
                    material_loss_rate=material_loss_rate,
                    scrap_recovery_rate=scrap_recovery_rate,
                    finished_finance_rate=finished_finance_rate,
                    finished_management_rate=finished_management_rate,
                    finished_warehouse_packaging_rate=finished_warehouse_packaging_rate,
                    finished_scrap_rate=finished_scrap_rate,
                    finished_pretax_profit_rate=finished_pretax_profit_rate,
                    created_by=audit["created_by"],
                    updated_by=audit["updated_by"],
                ),
            )
        else:
            self.repository.update_singleton(
                db,
                row,
                SystemConfigPatch(
                    app_name=app_name,
                    steel_density=steel_density,
                    material_loss_rate=material_loss_rate,
                    scrap_recovery_rate=scrap_recovery_rate,
                    finished_finance_rate=finished_finance_rate,
                    finished_management_rate=finished_management_rate,
                    finished_warehouse_packaging_rate=finished_warehouse_packaging_rate,
                    finished_scrap_rate=finished_scrap_rate,
                    finished_pretax_profit_rate=finished_pretax_profit_rate,
                    updated_by=audit_update(current_user)["updated_by"],
                ),
            )
        db.commit()
        return self.get_config(db)

    def get_steel_density(self, db: Session) -> Decimal:
        """核价用：读系统配置密度，无效或缺失则回退 7.85。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_STEEL_DENSITY
        return self._normalize_density(row.steel_density)

    def get_material_loss_rate(self, db: Session) -> Decimal:
        """核价用：读冲压材料损耗率，无效或缺失则回退 0.003（千分之3）。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_MATERIAL_LOSS_RATE
        return self._normalize_loss_rate(getattr(row, "material_loss_rate", None))

    def get_scrap_recovery_rate(self, db: Session) -> Decimal:
        """核价用：读废料回收率，无效或缺失则回退 0.97。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_SCRAP_RECOVERY_RATE
        return self._normalize_recovery_rate(getattr(row, "scrap_recovery_rate", None))

    def get_finished_finance_rate(self, db: Session) -> Decimal:
        """核价用：读成品财务费率，无效或缺失则回退 0.02。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_FINISHED_FINANCE_RATE
        return self._normalize_percent_rate(
            getattr(row, "finished_finance_rate", None),
            DEFAULT_FINISHED_FINANCE_RATE,
        )

    def get_finished_management_rate(self, db: Session) -> Decimal:
        """核价用：读成品管理费率，无效或缺失则回退 0.02。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_FINISHED_MANAGEMENT_RATE
        return self._normalize_percent_rate(
            getattr(row, "finished_management_rate", None),
            DEFAULT_FINISHED_MANAGEMENT_RATE,
        )

    def get_finished_warehouse_packaging_rate(self, db: Session) -> Decimal:
        """核价用：读仓储+包装管理费用率，无效或缺失则回退 0.01。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE
        return self._normalize_percent_rate(
            getattr(row, "finished_warehouse_packaging_rate", None),
            DEFAULT_FINISHED_WAREHOUSE_PACKAGING_RATE,
        )

    def get_finished_scrap_rate(self, db: Session) -> Decimal:
        """核价用：读成品报废率，无效或缺失则回退 0.003（千分之3）。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_FINISHED_SCRAP_RATE
        return self._normalize_permille_rate(
            getattr(row, "finished_scrap_rate", None),
            DEFAULT_FINISHED_SCRAP_RATE,
        )

    def get_finished_pretax_profit_rate(self, db: Session) -> Decimal:
        """核价用：读成品税前利润率，无效或缺失则回退 0.02。"""
        row = self.repository.get_singleton(db)
        if row is None:
            return DEFAULT_FINISHED_PRETAX_PROFIT_RATE
        return self._normalize_percent_rate(
            getattr(row, "finished_pretax_profit_rate", None),
            DEFAULT_FINISHED_PRETAX_PROFIT_RATE,
        )

    @staticmethod
    def _normalize_density(value: Any) -> Decimal:
        try:
            density = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return DEFAULT_STEEL_DENSITY
        if density <= 0:
            return DEFAULT_STEEL_DENSITY
        return quantize_money(density, Q4)

    @staticmethod
    def _normalize_loss_rate(value: Any) -> Decimal:
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return DEFAULT_MATERIAL_LOSS_RATE
        if rate < 0:
            return DEFAULT_MATERIAL_LOSS_RATE
        return quantize_money(rate, Q6)

    @staticmethod
    def _normalize_recovery_rate(value: Any) -> Decimal:
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return DEFAULT_SCRAP_RECOVERY_RATE
        if rate <= 0 or rate > 1:
            return DEFAULT_SCRAP_RECOVERY_RATE
        return quantize_money(rate, Q6)

    @staticmethod
    def _normalize_percent_rate(value: Any, default: Decimal) -> Decimal:
        """百分比费率（0~1，含 0）。"""
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default
        if rate < 0 or rate > 1:
            return default
        return quantize_money(rate, Q6)

    @staticmethod
    def _normalize_permille_rate(value: Any, default: Decimal) -> Decimal:
        """千分率（≥0）。"""
        try:
            rate = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default
        if rate < 0:
            return default
        return quantize_money(rate, Q6)
