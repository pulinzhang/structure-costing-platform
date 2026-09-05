"""核价用系统费率（密度 / 损耗 / 回收 / 成品四项 / 摆剪钢价加价）。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.settings.system.settings_service import SettingsService


@dataclass(frozen=True, slots=True)
class PartCostCalcRates:
    density: Decimal
    loss_rate: Decimal
    recovery_rate: Decimal
    finance_rate: Decimal
    management_rate: Decimal
    warehouse_packaging_rate: Decimal
    pretax_profit_rate: Decimal
    swing_shear_fee_per_ton: Decimal


def load_part_cost_calc_rates(settings: SettingsService, db: Session) -> PartCostCalcRates:
    return PartCostCalcRates(
        density=settings.get_steel_density(db),
        loss_rate=settings.get_material_loss_rate(db),
        recovery_rate=settings.get_scrap_recovery_rate(db),
        finance_rate=settings.get_finished_finance_rate(db),
        management_rate=settings.get_finished_management_rate(db),
        warehouse_packaging_rate=settings.get_finished_warehouse_packaging_rate(db),
        pretax_profit_rate=settings.get_finished_pretax_profit_rate(db),
        swing_shear_fee_per_ton=settings.get_swing_shear_process_fee_per_ton(db),
    )
