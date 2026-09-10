"""
仪表盘 Service
管理者看板：聚合上游切片，解读为待办 / 就绪 / 本期产出
"""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple

from sqlalchemy.orm import Session

from app.common.money import parse_decimal
from app.common.scrap_categories import SCRAP_CATEGORY_STEEL
from app.common.timezone import now
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
from app.schemas.dto.stamping_part_dto import StampingCascadeFilterQuery
from app.schemas.vo.dashboard_vo import (
    DashboardAttentionItemVO,
    DashboardAuditBucketVO,
    DashboardBomStatsVO,
    DashboardMasterStatsVO,
    DashboardOutcomeVO,
    DashboardReadinessVO,
    DashboardScopeVO,
    DashboardStatsVO,
    DashboardYishiyiyiStatsVO,
    SteelPriceCalcFilterOptionsVO,
    SteelPriceCalcStatsVO,
)
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.steel_grade_category import SteelGradeCategoryService
from app.services.stamping.stamping_service import StampingPartService
from app.services.yishiyiyi.base_price.steel_base_price_service import SteelBasePriceService
from app.services.yishiyiyi.policy.steel_price_policy_service import (
    SteelPricePolicyService,
)
from app.services.yishiyiyi.scrap_price.scrap_price_service import (
    StampingScrapPriceService,
)


class _ScrapStatus(NamedTuple):
    filled_count: int
    required_count: int
    is_complete: bool
    scrap_location: str | None
    is_scrap_location_filled: bool | None
    scrap_location_net_price: Decimal | None


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
        scope = self._resolve_scope(
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

        scrap_status = self._scrap_month_status(
            db, year=scope.year, month=scope.month, location=scope.location
        )
        bom = self._bom_coverage(
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
        base_price_count, policy_count = self._count_base_and_policy(
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

        readiness = self._build_readiness(yishiyiyi, process_fee, steel_price, part_cost)
        outcome = self._build_outcome(process_fee, steel_price, part_cost)
        attention = self._build_attention(
            master=master,
            yishiyiyi=yishiyiyi,
            process_fee=process_fee,
            steel_price=steel_price,
            part_cost=part_cost,
            bom=bom,
        )

        return DashboardStatsVO(
            scope=scope,
            outcome=outcome,
            readiness=readiness,
            attention=attention,
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
        filters = self._build_steel_calc_filter_options(db, location=location)
        if vehicle_model and vehicle_model not in filters.vehicle_models:
            vehicle_model = None

        base_price_count, adjustment_rule_count = self._count_base_and_policy(
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

    def _build_outcome(
        self,
        process_fee: DashboardAuditBucketVO,
        steel_price: DashboardAuditBucketVO,
        part_cost: DashboardAuditBucketVO,
    ) -> DashboardOutcomeVO:
        return DashboardOutcomeVO(
            pending_total=(
                process_fee.pending_count + steel_price.pending_count + part_cost.pending_count
            ),
            process_fee_pending=process_fee.pending_count,
            steel_price_pending=steel_price.pending_count,
            part_cost_pending=part_cost.pending_count,
            process_fee_zero=int(process_fee.zero_count or 0),
            part_cost_approved=part_cost.approved_count,
            part_cost_avg=part_cost.avg_value,
            steel_price_avg=steel_price.avg_value,
            process_fee_avg=process_fee.avg_value,
        )

    def _build_readiness(
        self,
        yishiyiyi: DashboardYishiyiyiStatsVO,
        process_fee: DashboardAuditBucketVO,
        steel_price: DashboardAuditBucketVO,
        part_cost: DashboardAuditBucketVO,
    ) -> DashboardReadinessVO:
        has_process_fee = (process_fee.total_count or 0) > 0
        has_steel = steel_price.pending_count + steel_price.approved_count > 0
        has_part = part_cost.pending_count + part_cost.approved_count > 0
        if yishiyiyi.is_scrap_location_filled is not None:
            scrap_ok = bool(yishiyiyi.is_scrap_location_filled)
        else:
            scrap_ok = yishiyiyi.is_scrap_complete
        flags = (
            yishiyiyi.base_price_count > 0,
            yishiyiyi.policy_count > 0,
            scrap_ok,
            has_process_fee,
            has_steel,
            has_part,
        )
        return DashboardReadinessVO(
            has_base_price=flags[0],
            has_policy=flags[1],
            is_scrap_complete=flags[2],
            has_process_fee=flags[3],
            has_steel_price=flags[4],
            has_part_cost=flags[5],
            ready_count=sum(1 for flag in flags if flag),
            total_count=len(flags),
        )

    def _build_attention(
        self,
        *,
        master: DashboardMasterStatsVO,
        yishiyiyi: DashboardYishiyiyiStatsVO,
        process_fee: DashboardAuditBucketVO,
        steel_price: DashboardAuditBucketVO,
        part_cost: DashboardAuditBucketVO,
        bom: DashboardBomStatsVO,
    ) -> list[DashboardAttentionItemVO]:
        items: list[DashboardAttentionItemVO] = []

        if master.parts == 0:
            items.append(
                DashboardAttentionItemVO(
                    code="master_empty",
                    severity="critical",
                    title="冲压主数据为空",
                    detail="尚未入库工艺零件，无法开展加工费与冲压零件核价",
                    page="stamping-upload",
                )
            )

        if yishiyiyi.base_price_count == 0:
            items.append(
                DashboardAttentionItemVO(
                    code="base_price_missing",
                    severity="critical",
                    title="当期无中标基价",
                    detail="钢材联动计算缺少基价依据",
                    page="base-price-download",
                )
            )
        if yishiyiyi.policy_count == 0:
            items.append(
                DashboardAttentionItemVO(
                    code="policy_missing",
                    severity="warning",
                    title="当期无加减价政策",
                    detail="厚宽调价规则未入库，联动价可能不完整",
                    page="steel-price-policy-download",
                )
            )
        if yishiyiyi.is_scrap_location_filled is False:
            loc_label = yishiyiyi.scrap_location or "所选基地"
            items.append(
                DashboardAttentionItemVO(
                    code="scrap_incomplete",
                    severity="warning",
                    title=f"{loc_label}废料价未录入",
                    detail="当期该基地废料净价缺失，冲压零件核价扣减可能不全",
                    page="scrap-price",
                )
            )
        elif yishiyiyi.is_scrap_location_filled is None and not yishiyiyi.is_scrap_complete:
            items.append(
                DashboardAttentionItemVO(
                    code="scrap_incomplete",
                    severity="warning",
                    title="废料月度价未齐",
                    detail=(
                        f"已录 {yishiyiyi.scrap_filled_count}/"
                        f"{yishiyiyi.scrap_required_count}，冲压零件核价扣减可能不全"
                    ),
                    count=yishiyiyi.scrap_required_count - yishiyiyi.scrap_filled_count,
                    page="scrap-price",
                )
            )

        zero = int(process_fee.zero_count or 0)
        if zero > 0:
            items.append(
                DashboardAttentionItemVO(
                    code="process_fee_zero",
                    severity="warning",
                    title="加工费待补价",
                    detail="存在零价 / 需手工补价记录，影响冲压零件核价",
                    count=zero,
                    page="stamping-process-fee",
                )
            )
        if process_fee.pending_count > 0:
            items.append(
                DashboardAttentionItemVO(
                    code="process_fee_pending",
                    severity="warning",
                    title="加工费待审核",
                    detail="审核通过后方可作为冲压零件核价依据",
                    count=process_fee.pending_count,
                    page="stamping-process-fee",
                )
            )
        if steel_price.pending_count > 0:
            items.append(
                DashboardAttentionItemVO(
                    code="steel_price_pending",
                    severity="warning",
                    title="钢材联动价待审核",
                    detail="待审联动价尚未锁定",
                    count=steel_price.pending_count,
                    page="steel-price-list",
                )
            )
        if part_cost.pending_count > 0:
            items.append(
                DashboardAttentionItemVO(
                    code="part_cost_pending",
                    severity="warning",
                    title="冲压零件价格待审核",
                    detail="本期冲压件核价结果等待管理者确认",
                    count=part_cost.pending_count,
                    page="stamping-part-cost",
                )
            )

        has_steel = steel_price.pending_count + steel_price.approved_count > 0
        has_part = part_cost.pending_count + part_cost.approved_count > 0
        if yishiyiyi.base_price_count > 0 and not has_steel:
            items.append(
                DashboardAttentionItemVO(
                    code="steel_price_empty",
                    severity="info",
                    title="本期尚未算出钢材联动价",
                    detail="基价已就绪，可发起联动计算",
                    page="steel-price-calc",
                )
            )
        if (process_fee.total_count or 0) > 0 and has_steel and not has_part:
            items.append(
                DashboardAttentionItemVO(
                    code="part_cost_empty",
                    severity="info",
                    title="本期尚未核算冲压零件价格",
                    detail="加工费与钢价已有数据，可发起冲压零件核价",
                    page="stamping-part-cost-calc",
                )
            )
        if bom.snapshot_count == 0:
            items.append(
                DashboardAttentionItemVO(
                    code="bom_empty",
                    severity="info",
                    title="BOM 清单未覆盖",
                    detail="材料清单版本为空，结构核对受限",
                    page="bom-structure",
                )
            )

        severity_rank = {"critical": 0, "warning": 1, "info": 2}
        items.sort(key=lambda item: (severity_rank.get(item.severity, 9), item.code))
        return items

    def _resolve_scope(
        self,
        db: Session,
        *,
        year: int | None,
        month: int | None,
        location: str | None,
        vehicle_model: str | None,
    ) -> DashboardScopeVO:
        years, months_all, locations = self._collect_scope_options(db)
        clock = now()

        resolved_year = year if year is not None else (years[0] if years else clock.year)
        months_for_year = self._months_for_year(db, resolved_year, fallback=months_all)
        if not months_for_year:
            months_for_year = list(range(1, 13))

        # 默认优先「有基价/钢价/零件价」的最近月，避免落到仅有废料的空核价月
        preferred = self._preferred_months(db, resolved_year)

        if month is not None and 1 <= month <= 12:
            resolved_month = month
        elif preferred:
            resolved_month = max(preferred)
        elif months_for_year:
            resolved_month = max(months_for_year)
        else:
            resolved_month = clock.month

        if location and location not in locations:
            locations = sorted({*locations, location})

        cascade = self.stamping_service.get_cascade_filter_options(
            db,
            StampingCascadeFilterQuery(location=location),
        )
        vehicle_models = list(cascade.vehicle_models)
        resolved_vehicle = vehicle_model if vehicle_model in vehicle_models else None

        return DashboardScopeVO(
            year=resolved_year,
            month=resolved_month,
            location=location,
            vehicle_model=resolved_vehicle,
            years=years or [resolved_year],
            months=sorted(set(months_for_year)),
            locations=locations,
            vehicle_models=vehicle_models,
        )

    def _preferred_months(self, db: Session, year: int) -> list[int]:
        months: set[int] = set()
        months.update(self.base_price_repo.get_distinct_months_for_year(db, year))
        months.update(self.steel_price_repo.get_distinct_months_for_year(db, year))
        months.update(self.policy_repo.get_distinct_months_for_year(db, year))
        months.update(self.part_cost_repo.get_distinct_months(db, year=year))
        return sorted(months)

    def _collect_scope_options(self, db: Session) -> tuple[list[int], list[int], list[str]]:
        base_opts = self.base_price_service.get_filter_options(db)
        policy_opts = self.policy_service.get_filter_options(db)
        scrap_opts = self.scrap_service.get_filter_options(db)
        steel_opts = self.steel_price_repo.get_filter_options(db)
        part_years = self.part_cost_repo.get_distinct_years(db)

        years = sorted(
            set(base_opts.years)
            | set(policy_opts.years)
            | set(scrap_opts.years)
            | set(steel_opts.get("years") or [])
            | set(part_years),
            reverse=True,
        )
        months = sorted(
            set(base_opts.months) | set(policy_opts.months) | set(steel_opts.get("months") or [])
        )
        locations = LocationService().list_registered(db)
        return years, months, locations

    def _months_for_year(
        self,
        db: Session,
        year: int,
        *,
        fallback: list[int],
    ) -> list[int]:
        months: set[int] = set(self._preferred_months(db, year))
        for summary in self.scrap_service.list_month_summaries(
            db, year=year, scrap_category=SCRAP_CATEGORY_STEEL
        ):
            months.add(summary.month)
        if months:
            return sorted(months)
        return list(fallback)

    def _scrap_month_status(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str | None = None,
    ) -> _ScrapStatus:
        sheet = self.scrap_service.get_month_sheet(db, year, month, SCRAP_CATEGORY_STEEL)

        scrap_location: str | None = None
        is_scrap_location_filled: bool | None = None
        scrap_location_net_price: Decimal | None = None
        if location:
            scrap_location = location
            row = next((r for r in sheet.items if r.location == location), None)
            if row is None:
                aliases = LocationService().expand_for_query(db, location)
                row = next(
                    (r for r in sheet.items if r.location in aliases),
                    None,
                )
            if row is not None and row.net_price is not None:
                is_scrap_location_filled = True
                scrap_location_net_price = parse_decimal(row.net_price)
            else:
                is_scrap_location_filled = False

        status = _ScrapStatus(
            filled_count=int(sheet.filled_count),
            required_count=int(sheet.required_count),
            is_complete=bool(sheet.is_complete),
            scrap_location=scrap_location,
            is_scrap_location_filled=is_scrap_location_filled,
            scrap_location_net_price=scrap_location_net_price,
        )
        return status

    def _bom_coverage(
        self,
        db: Session,
        *,
        location: str | None,
        vehicle_model: str | None = None,
    ) -> DashboardBomStatsVO:
        _, snapshot_count = self.bom_snapshot_repo.paginate(
            db,
            location=location,
            vehicle_model=vehicle_model,
            skip=0,
            limit=1,
        )
        node_count = self.bom_snapshot_repo.count_all_nodes(
            db,
            location=location,
            vehicle_model=vehicle_model,
        )
        return DashboardBomStatsVO(
            snapshot_count=int(snapshot_count),
            node_count=node_count,
        )

    def _count_base_and_policy(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str | None,
        vehicle_model: str | None,
    ) -> tuple[int, int]:
        """
        基价 / 政策条数。未选项目时按年+月+基地（政策全国）。
        选了项目则按该项目工艺牌号覆盖：基价 grade IN 牌号，政策按牌号分类收窄。
        """
        if not vehicle_model:
            return (
                self.base_price_service.count_by_conditions(
                    db,
                    year=year,
                    month=month,
                    location=location,
                ),
                self.policy_service.count_policies(
                    db,
                    year=year,
                    month=month,
                ),
            )

        grades = self.stamping_service.list_distinct_spec_grades(
            db,
            location=location,
            vehicle_model=vehicle_model,
        )
        if not grades:
            return 0, 0

        base_count = self.base_price_service.count_by_conditions(
            db,
            year=year,
            month=month,
            location=location,
            grades_in=grades,
        )
        mapped = self.grade_category_service.map_grades(db, grades)
        categories = sorted({vo.category_name for vo in mapped.values() if vo.category_name})
        if not categories:
            return base_count, 0
        policy_count = self.policy_service.count_policies(
            db,
            year=year,
            month=month,
            category_names=categories,
        )
        return base_count, policy_count

    def _build_steel_calc_filter_options(
        self,
        db: Session,
        *,
        location: str | None = None,
    ) -> SteelPriceCalcFilterOptionsVO:
        base_opts = self.base_price_service.get_filter_options(db)
        policy_opts = self.policy_service.get_filter_options(db)
        years = sorted(set(base_opts.years) | set(policy_opts.years), reverse=True)
        months = sorted(set(base_opts.months) | set(policy_opts.months))
        cascade = self.stamping_service.get_cascade_filter_options(
            db,
            StampingCascadeFilterQuery(location=location),
        )
        return SteelPriceCalcFilterOptionsVO(
            years=years,
            months=months,
            locations=list(base_opts.locations),
            vehicle_models=list(cascade.vehicle_models),
        )
