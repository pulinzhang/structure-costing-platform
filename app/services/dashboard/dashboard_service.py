"""
仪表盘 Service
管理者看板：聚合上游切片，解读为待办 / 就绪 / 本期产出
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.bom.bom_repository import BomSnapshotRepository
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.repositories.costing.steel_price.steel_price_repository import (
    SteelPriceRepository,
)
from app.repositories.stamping.stamping_process_fee_repository import (
    StampingProcessFeeRepository,
)
from app.repositories.yishiyiyi.base_price.steel_base_price_repository import (
    SteelBasePriceRepository,
)
from app.repositories.yishiyiyi.policy.steel_price_policy_repository import (
    SteelPricePolicyRepository,
)
from app.schemas.vo.dashboard_vo import (
    DashboardAuditBucketVO,
    DashboardMasterStatsVO,
    DashboardStatsVO,
    DashboardYishiyiyiStatsVO,
    SteelPriceCalcStatsVO,
)
from app.services.dashboard.attention import build_attention
from app.services.dashboard.coverage import (
    bom_coverage,
    build_steel_calc_filter_options,
    count_base_and_policy,
)
from app.services.dashboard.readiness import build_outcome, build_readiness
from app.services.dashboard.scope import resolve_scope
from app.services.dashboard.scrap import scrap_month_status
from app.services.masterdata.steel_grade_category import SteelGradeCategoryService
from app.services.stamping.stamping_service import StampingPartService
from app.services.yishiyiyi.base_price.steel_base_price_service import SteelBasePriceService
from app.services.yishiyiyi.policy.steel_price_policy_service import (
    SteelPricePolicyService,
)
from app.services.yishiyiyi.scrap_price.scrap_price_service import (
    StampingScrapPriceService,
)


class DashboardService:
    """仪表盘业务逻辑：下游组合上游切片，输出管理者解读。"""

    def __init__(self) -> None:
        self.base_price_service = SteelBasePriceService()
        self.policy_service = SteelPricePolicyService()
        self.scrap_service = StampingScrapPriceService()
        self.stamping_service = StampingPartService()
        self.grade_category_service = SteelGradeCategoryService()
        self.process_fee_repo = StampingProcessFeeRepository()
        self.steel_price_repo = SteelPriceRepository()
        self.part_cost_repo = StampingPartCostRepository()
        self.bom_snapshot_repo = BomSnapshotRepository()
        self.base_price_repo = SteelBasePriceRepository()
        self.policy_repo = SteelPricePolicyRepository()

    def get_all_stats(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> DashboardStatsVO:
        """管理者看板汇总。"""
        location_clean = location.strip() if location else None
        vehicle_clean = vehicle_model.strip() if vehicle_model else None
        scope = resolve_scope(
            self,
            db,
            year=year,
            month=month,
            location=location_clean,
            vehicle_model=vehicle_clean,
        )
        vehicle_clean = scope.vehicle_model

        fee_summary = self.process_fee_repo.summarize_by_filters(
            db,
            year=scope.year,
            location=scope.location,
            vehicle_model=vehicle_clean,
        )
        steel_summary = self.steel_price_repo.summarize_by_filters(
            db,
            year=scope.year,
            month=scope.month,
            location=scope.location,
        )
        part_summary = self.part_cost_repo.summarize_by_filters(
            db,
            year=scope.year,
            month=scope.month,
            location=scope.location,
            vehicle_model=vehicle_clean,
        )

        scrap_status = scrap_month_status(
            self, db, year=scope.year, month=scope.month, location=scope.location
        )
        bom = bom_coverage(
            self,
            db,
            location=scope.location,
            vehicle_model=vehicle_clean,
        )

        master_raw = self.stamping_service.summarize_master(
            db,
            location=scope.location,
            vehicle_model=vehicle_clean,
        )
        master = DashboardMasterStatsVO(
            parts=master_raw["parts"],
            processes=master_raw["processes"],
            models=master_raw["models"],
        )
        base_price_count, policy_count = count_base_and_policy(
            self,
            db,
            year=scope.year,
            month=scope.month,
            location=scope.location,
            vehicle_model=vehicle_clean,
        )
        yishiyiyi = DashboardYishiyiyiStatsVO(
            base_price_count=base_price_count,
            policy_count=policy_count,
            scrap_filled_count=scrap_status.filled_count,
            scrap_required_count=scrap_status.required_count,
            is_scrap_complete=scrap_status.is_complete,
            scrap_location=scrap_status.scrap_location,
            is_scrap_location_filled=scrap_status.is_scrap_location_filled,
            scrap_location_net_price=scrap_status.scrap_location_net_price,
        )
        process_fee = DashboardAuditBucketVO(
            pending_count=int(fee_summary.get("pending_count") or 0),
            approved_count=int(fee_summary.get("approved_count") or 0),
            zero_count=int(fee_summary.get("zero_count") or 0),
            total_count=int(fee_summary.get("total_count") or 0),
            avg_value=fee_summary.get("avg_fee"),
        )
        steel_price = DashboardAuditBucketVO(
            pending_count=int(steel_summary.get("pending_count") or 0),
            approved_count=int(steel_summary.get("approved_count") or 0),
            avg_value=steel_summary.get("avg_final_price"),
        )
        part_cost = DashboardAuditBucketVO(
            pending_count=int(part_summary.get("pending_count") or 0),
            approved_count=int(part_summary.get("approved_count") or 0),
            avg_value=part_summary.get("avg_unit_cost"),
        )

        return DashboardStatsVO(
            scope=scope,
            outcome=build_outcome(process_fee, steel_price, part_cost),
            readiness=build_readiness(yishiyiyi, process_fee, steel_price, part_cost),
            attention=build_attention(
                master=master,
                yishiyiyi=yishiyiyi,
                process_fee=process_fee,
                steel_price=steel_price,
                part_cost=part_cost,
                bom=bom,
            ),
            master=master,
            yishiyiyi=yishiyiyi,
            process_fee=process_fee,
            steel_price=steel_price,
            part_cost=part_cost,
            bom=bom,
        )

    def get_steel_price_calc_stats(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> SteelPriceCalcStatsVO:
        """钢价联动计算页数据依据统计。"""
        location = location.strip() if location else None
        vehicle_model = vehicle_model.strip() if vehicle_model else None
        filters = build_steel_calc_filter_options(self, db, location=location)
        if vehicle_model and vehicle_model not in filters.vehicle_models:
            vehicle_model = None

        base_price_count, adjustment_rule_count = count_base_and_policy(
            self,
            db,
            year=year,
            month=month,
            location=location,
            vehicle_model=vehicle_model,
        )

        if not location:
            thickness_row_count = 0
        else:
            thickness_row_count = self.stamping_service.count_material_specs(
                db,
                location=location,
                vehicle_model=vehicle_model,
            )

        return SteelPriceCalcStatsVO(
            base_price_count=base_price_count,
            adjustment_rule_count=adjustment_rule_count,
            thickness_row_count=thickness_row_count,
            filters=filters,
        )
