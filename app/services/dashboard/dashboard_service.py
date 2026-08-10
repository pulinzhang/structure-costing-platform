"""
仪表盘 Service
聚合跨切片统计数据，供 Router 封装为 ApiResponse
"""

from sqlalchemy.orm import Session

from app.schemas.vo.dashboard_vo import (
    SteelPriceCalcFilterOptionsVO,
    SteelPriceCalcStatsVO,
)
from app.services.steel_base_price.steel_base_price_service import SteelBasePriceService
from app.services.steel_price_policy.steel_price_policy_service import (
    SteelPricePolicyService,
)
from app.services.stamping.stamping_service import StampingPartService


class DashboardService:
    """仪表盘业务逻辑"""

    def __init__(self) -> None:
        self.base_price_service = SteelBasePriceService()
        self.policy_service = SteelPricePolicyService()
        self.stamping_service = StampingPartService()

    def get_steel_price_calc_stats(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
    ) -> SteelPriceCalcStatsVO:
        """
        钢价联动计算页数据依据统计：
        - 中标基价库 / 厚宽调价规则 / 厚度规格行数
        - 同时返回年度、月份筛选选项
        """
        location = location.strip() if location else None
        stamping_supplier = stamping_supplier.strip() if stamping_supplier else None
        vehicle_model = vehicle_model.strip() if vehicle_model else None

        base_price_count = self.base_price_service.count_by_conditions(
            db,
            year=year,
            month=month,
            location=location,
        )
        adjustment_rule_count = self.policy_service.count_policies(
            db,
            year=year,
            month=month,
        )

        # 基地 / 冲压工厂 / 配套车型 全空时，厚度规格行数固定为 0
        if not location and not stamping_supplier and not vehicle_model:
            thickness_row_count = 0
        else:
            thickness_row_count = self.stamping_service.count_material_specs(
                db,
                location=location,
                stamping_supplier=stamping_supplier,
                vehicle_model=vehicle_model,
            )

        return SteelPriceCalcStatsVO(
            base_price_count=base_price_count,
            adjustment_rule_count=adjustment_rule_count,
            thickness_row_count=thickness_row_count,
            filters=self._build_filter_options(db),
        )

    def _build_filter_options(self, db: Session) -> SteelPriceCalcFilterOptionsVO:
        base_opts = self.base_price_service.get_filter_options(db)
        policy_opts = self.policy_service.get_filter_options(db)

        years = sorted(set(base_opts.years) | set(policy_opts.years), reverse=True)
        months = sorted(set(base_opts.months) | set(policy_opts.months))
        return SteelPriceCalcFilterOptionsVO(
            years=years,
            months=months,
            locations=list(base_opts.locations),
        )
