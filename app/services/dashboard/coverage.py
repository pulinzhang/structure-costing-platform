"""仪表盘：BOM 覆盖、基价/政策条数、钢价计算筛选项。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.schemas.dto.stamping_part_dto import StampingCascadeFilterQuery
from app.schemas.vo.dashboard_vo import DashboardBomStatsVO, SteelPriceCalcFilterOptionsVO

if TYPE_CHECKING:
    from app.services.dashboard.service import DashboardService


def bom_coverage(
    svc: DashboardService,
    db: Session,
    *,
    location: str | None,
    vehicle_model: str | None = None,
) -> DashboardBomStatsVO:
    _, snapshot_count = svc.bom_snapshot_repo.paginate(
        db,
        location=location,
        vehicle_model=vehicle_model,
        skip=0,
        limit=1,
    )
    node_count = svc.bom_snapshot_repo.count_all_nodes(
        db,
        location=location,
        vehicle_model=vehicle_model,
    )
    return DashboardBomStatsVO(
        snapshot_count=int(snapshot_count),
        node_count=node_count,
    )


def count_base_and_policy(
    svc: DashboardService,
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
            svc.base_price_service.count_by_conditions(
                db,
                year=year,
                month=month,
                location=location,
            ),
            svc.policy_service.count_policies(
                db,
                year=year,
                month=month,
            ),
        )

    grades = svc.stamping_service.list_distinct_spec_grades(
        db,
        location=location,
        vehicle_model=vehicle_model,
    )
    if not grades:
        return 0, 0

    base_count = svc.base_price_service.count_by_conditions(
        db,
        year=year,
        month=month,
        location=location,
        grades_in=grades,
    )
    mapped = svc.grade_category_service.map_grades(db, grades)
    categories = sorted({vo.category_name for vo in mapped.values() if vo.category_name})
    if not categories:
        return base_count, 0
    policy_count = svc.policy_service.count_policies(
        db,
        year=year,
        month=month,
        category_names=categories,
    )
    return base_count, policy_count


def build_steel_calc_filter_options(
    svc: DashboardService,
    db: Session,
    *,
    location: str | None = None,
) -> SteelPriceCalcFilterOptionsVO:
    base_opts = svc.base_price_service.get_filter_options(db)
    policy_opts = svc.policy_service.get_filter_options(db)
    years = sorted(set(base_opts.years) | set(policy_opts.years), reverse=True)
    months = sorted(set(base_opts.months) | set(policy_opts.months))
    cascade = svc.stamping_service.get_cascade_filter_options(
        db,
        StampingCascadeFilterQuery(location=location),
    )
    return SteelPriceCalcFilterOptionsVO(
        years=years,
        months=months,
        locations=list(base_opts.locations),
        vehicle_models=list(cascade.vehicle_models),
    )
