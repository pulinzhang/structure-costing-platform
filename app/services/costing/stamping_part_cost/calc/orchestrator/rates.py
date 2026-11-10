"""核价用参数：密度、损耗、回收来自系统设置；成品四项来自计费管理里的冲压件。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services.costing.finished_rates import load_finished_fee_rates
from app.services.masterdata.category_billing.rates import STAMPING_CATEGORY_CODE
from app.services.settings.system.service import SettingsService


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
    finished = load_finished_fee_rates(db, STAMPING_CATEGORY_CODE)
    return PartCostCalcRates(
        density=settings.get_steel_density(db),
        loss_rate=settings.get_material_loss_rate(db),
        recovery_rate=settings.get_scrap_recovery_rate(db),
        finance_rate=finished.finance_rate,
        management_rate=finished.management_rate,
        warehouse_packaging_rate=finished.warehouse_packaging_rate,
        pretax_profit_rate=finished.pretax_profit_rate,
        swing_shear_fee_per_ton=settings.get_swing_shear_process_fee_per_ton(db),
    )
