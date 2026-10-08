"""钢材价格：列表分页与筛选下拉。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.costing import SteelPrice
from app.repositories.costing.steel_price.steel_price_repository import (
    SteelPriceRepository,
)
from app.schemas.dto.steel_price_dto import SteelPriceQuery
from app.schemas.vo.steel_price_vo import (
    SteelPriceFilterOptionsVO,
    SteelPriceListSummaryVO,
    SteelPriceResponse,
)
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.steel_mill.service import SteelMillService


def attach_mill_abbreviation(
    db: Session,
    records: list[SteelPrice],
) -> list[SteelPriceResponse]:
    """列表主字用档案缩写。结果行上的 steel_mill 仍是计算当时的字。"""
    hits = SteelMillService().hits_by_id(db)
    rows: list[SteelPriceResponse] = []
    for record in records:
        vo = SteelPriceResponse.model_validate(record)
        if record.steel_mill_id is not None:
            hit = hits.get(record.steel_mill_id)
            if hit is not None:
                vo.steel_mill_abbreviation = hit.abbreviation
        rows.append(vo)
    return rows


def _enabled_mill_abbreviations(db: Session) -> list[str]:
    return [item.abbreviation for item in SteelMillService().list_enabled(db)]


def paginate_steel_prices(
    repository: SteelPriceRepository,
    db: Session,
    query: SteelPriceQuery,
) -> tuple[list[SteelPriceResponse], int, SteelPriceListSummaryVO]:
    """当前筛选下的一页，以及同一套条件的总条数和汇总。不含下拉。"""
    skip = (query.page - 1) * query.size
    year = query.year
    month = query.month
    location_raw = query.location.strip() if query.location else None
    category_name = query.category_name.strip() if query.category_name else None
    grade = query.grade.strip() if query.grade else None
    steel_mill_id = SteelMillService().filter_id(db, query.steel_mill)
    audit_status = query.audit_status.strip() if query.audit_status else None
    locations: list[str] | None = None
    if location_raw:
        locations = LocationService().expand_for_query(db, location_raw)
        if not locations:
            return [], 0, SteelPriceListSummaryVO()
    records, total, summary = repository.paginate(
        db,
        year=year,
        month=month,
        locations=locations,
        category_name=category_name,
        grade=grade,
        steel_mill_id=steel_mill_id,
        audit_status=audit_status,
        skip=skip,
        limit=query.size,
    )
    return (
        attach_mill_abbreviation(db, records),
        total,
        SteelPriceListSummaryVO.model_validate(summary),
    )


def steel_price_filter_options(
    repository: SteelPriceRepository,
    db: Session,
) -> SteelPriceFilterOptionsVO:
    """下拉：表里有哪些年度、月份、基地、品类、钢厂、审核状态。"""
    options = repository.get_filter_options(db)
    return SteelPriceFilterOptionsVO(
        years=list(options["years"]),
        months=list(options["months"]),
        locations=LocationService().list_registered(db),
        category_names=list(options["category_names"]),
        steel_mills=_enabled_mill_abbreviations(db),
        audit_statuses=list(options["audit_statuses"]),
    )
