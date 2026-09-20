"""钢材价格：列表分页与筛选下拉。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.costing.steel_price.steel_price_repository import (
    SteelPriceRepository,
)
from app.schemas.dto.steel_price_dto import SteelPriceQuery
from app.schemas.vo.steel_price_vo import (
    SteelPriceFilterOptionsVO,
    SteelPriceListSummaryVO,
    SteelPriceResponse,
)
from app.services.masterdata.location.location_service import LocationService


def paginate_steel_prices(
    repository: SteelPriceRepository,
    db: Session,
    query: SteelPriceQuery,
) -> tuple[list[SteelPriceResponse], int, SteelPriceFilterOptionsVO]:
    skip = (query.page - 1) * query.size
    year = query.year
    month = query.month
    location_raw = query.location.strip() if query.location else None
    category_name = query.category_name.strip() if query.category_name else None
    grade = query.grade.strip() if query.grade else None
    steel_mill = query.steel_mill.strip() if query.steel_mill else None
    audit_status = query.audit_status.strip() if query.audit_status else None
    location_service = LocationService()
    locations: list[str] | None = None
    if location_raw:
        locations = location_service.expand_for_query(db, location_raw)
        if not locations:
            options = repository.get_filter_options(db)
            return (
                [],
                0,
                SteelPriceFilterOptionsVO(
                    years=list(options["years"]),
                    months=list(options["months"]),
                    locations=location_service.list_registered(db),
                    category_names=list(options["category_names"]),
                    steel_mills=list(options["steel_mills"]),
                    audit_statuses=list(options["audit_statuses"]),
                    summary=SteelPriceListSummaryVO(),
                ),
            )
    records, total = repository.paginate(
        db,
        year=year,
        month=month,
        locations=locations,
        category_name=category_name,
        grade=grade,
        steel_mill=steel_mill,
        audit_status=audit_status,
        skip=skip,
        limit=query.size,
    )
    rows = [SteelPriceResponse.model_validate(record) for record in records]
    options = repository.get_filter_options(db)
    filters = SteelPriceFilterOptionsVO(
        years=list(options["years"]),
        months=list(options["months"]),
        locations=location_service.list_registered(db),
        category_names=list(options["category_names"]),
        steel_mills=list(options["steel_mills"]),
        audit_statuses=list(options["audit_statuses"]),
        summary=SteelPriceListSummaryVO.model_validate(
            repository.summarize_by_filters(
                db,
                year=year,
                month=month,
                locations=locations,
                category_name=category_name,
                grade=grade,
                steel_mill=steel_mill,
                audit_status=audit_status,
            )
        ),
    )
    return rows, total, filters
