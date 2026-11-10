"""冲压件与总成共用的成品费率。开关在系统设置，数字在计费管理。"""

from sqlalchemy.orm import Session

from app.services.masterdata.category_billing.rates import FinishedFeeRates
from app.services.masterdata.category_billing.service import AssemblyCategoryBillingService
from app.services.settings.system.service import SettingsService


def load_finished_fee_rates(db: Session, category_code: str) -> FinishedFeeRates:
    if not SettingsService().calculates_finished_rates(db):
        return FinishedFeeRates.zeros()
    return AssemblyCategoryBillingService().finished_fee_rates(db, category_code=category_code)
