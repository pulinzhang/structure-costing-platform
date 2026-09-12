"""仪表盘：默认年/月/基地/项目范围。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.common.scrap_categories import SCRAP_CATEGORY_STEEL
from app.common.timezone import now
from app.schemas.dto.stamping_part_dto import StampingCascadeFilterQuery
from app.schemas.vo.dashboard_vo import DashboardScopeVO
from app.services.masterdata.location.location_service import LocationService

if TYPE_CHECKING:
    from app.services.dashboard.dashboard_service import DashboardService


def preferred_months(svc: DashboardService, db: Session, year: int) -> list[int]:
    months: set[int] = set()
    months.update(svc.base_price_repo.get_distinct_months_for_year(db, year))
    months.update(svc.steel_price_repo.get_distinct_months_for_year(db, year))
    months.update(svc.policy_repo.get_distinct_months_for_year(db, year))
    months.update(svc.part_cost_repo.get_distinct_months(db, year=year))
    return sorted(months)


def collect_scope_options(
    svc: DashboardService, db: Session
) -> tuple[list[int], list[int], list[str]]:
    base_opts = svc.base_price_service.get_filter_options(db)
    policy_opts = svc.policy_service.get_filter_options(db)
    scrap_opts = svc.scrap_service.get_filter_options(db)
    steel_opts = svc.steel_price_repo.get_filter_options(db)
    part_years = svc.part_cost_repo.get_distinct_years(db)

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


def months_for_year(
    svc: DashboardService,
    db: Session,
    year: int,
    *,
    fallback: list[int],
) -> list[int]:
    months: set[int] = set(preferred_months(svc, db, year))
    for summary in svc.scrap_service.list_month_summaries(
        db, year=year, scrap_category=SCRAP_CATEGORY_STEEL
    ):
        months.add(summary.month)
    if months:
        return sorted(months)
    return list(fallback)


def resolve_scope(
    svc: DashboardService,
    db: Session,
    *,
    year: int | None,
    month: int | None,
    location: str | None,
    vehicle_model: str | None,
) -> DashboardScopeVO:
    years, months_all, locations = collect_scope_options(svc, db)
    clock = now()

    resolved_year = year if year is not None else (years[0] if years else clock.year)
    months_for_resolved = months_for_year(svc, db, resolved_year, fallback=months_all)
    if not months_for_resolved:
        months_for_resolved = list(range(1, 13))

    # 默认优先「有基价/钢价/零件价」的最近月，避免落到仅有废料的空核价月
    preferred = preferred_months(svc, db, resolved_year)

    if month is not None and 1 <= month <= 12:
        resolved_month = month
    elif preferred:
        resolved_month = max(preferred)
    elif months_for_resolved:
        resolved_month = max(months_for_resolved)
    else:
        resolved_month = clock.month

    if location and location not in locations:
        locations = sorted({*locations, location})

    cascade = svc.stamping_service.get_cascade_filter_options(
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
        months=sorted(set(months_for_resolved)),
        locations=locations,
        vehicle_models=vehicle_models,
    )
