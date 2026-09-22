"""冲压零件核价：列表分页、单条查询与展示字段。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.exceptions.base import NotFoundException
from app.models.costing import StampingPartCost
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    PartCostListFilters,
    StampingPartCostRepository,
    empty_part_cost_summary,
)
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.stamping.part.tailor_weld_blank import (
    StampingTailorWeldBlankRepository,
)
from app.schemas.dto.stamping_part_cost_dto import StampingPartCostQuery
from app.schemas.vo.stamping_part_cost_vo import StampingPartCostVO
from app.services.costing.stamping_part_cost.export.tailor_weld_display import (
    build_steel_price_index,
    load_blanks_by_part_id,
    resolve_part_cost_display,
)
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.supplier.service import SupplierService
from app.services.masterdata.vehicle_model.service import VehicleModelService


def to_cost_vos(
    db: Session,
    rows: list[StampingPartCost],
    *,
    blank_repo: StampingTailorWeldBlankRepository,
    steel_repo: SteelPriceRepository,
) -> list[StampingPartCostVO]:
    if not rows:
        return []
    blanks_by_part = load_blanks_by_part_id(db, rows, blank_repo=blank_repo)
    price_index = build_steel_price_index(db, rows, steel_repo=steel_repo)
    result: list[StampingPartCostVO] = []
    for row in rows:
        display = resolve_part_cost_display(
            row,
            blanks_by_part.get(row.source_part_id, []),
            price_index,
        )
        vo = StampingPartCostVO.model_validate(row)
        result.append(
            vo.model_copy(
                update={
                    "thickness": display.thickness,
                    "sheet_length": display.sheet_length,
                    "sheet_width": display.sheet_width,
                    "steel_ton_price": display.steel_ton_price,
                }
            )
        )
    return result


def empty_filters(
    cost_repo: StampingPartCostRepository,
    db: Session,
    query: StampingPartCostQuery,
    location_service: LocationService,
) -> PartCostListFilters:
    return {
        "years": cost_repo.get_distinct_years(db),
        "months": cost_repo.get_distinct_months(db, year=query.year),
        "locations": location_service.list_registered(db),
        "suppliers": SupplierService().list_registered_names(db),
        "vehicle_models": VehicleModelService().list_filter_codes(db, query.location),
        "versions": [],
        "summary": empty_part_cost_summary(),
    }


def paginate_costs(
    cost_repo: StampingPartCostRepository,
    blank_repo: StampingTailorWeldBlankRepository,
    steel_repo: SteelPriceRepository,
    db: Session,
    query: StampingPartCostQuery,
) -> tuple[list[StampingPartCostVO], int, PartCostListFilters]:
    skip = (query.page - 1) * query.size
    location_service = LocationService()
    locations: list[str] | None = None
    if query.location:
        locations = location_service.expand_for_query(db, query.location)
        if not locations:
            return [], 0, empty_filters(cost_repo, db, query, location_service)
    supplier_names = SupplierService().names_for_query(db, query.stamping_supplier)
    if supplier_names is not None and not supplier_names:
        return [], 0, empty_filters(cost_repo, db, query, location_service)
    rows, total = cost_repo.paginate(
        db,
        year=query.year,
        month=query.month,
        locations=locations,
        stamping_suppliers=supplier_names,
        vehicle_model=query.vehicle_model,
        version=query.version,
        part_number=query.part_number,
        audit_status=query.audit_status,
        skip=skip,
        limit=query.size,
    )
    filters: PartCostListFilters = {
        "years": cost_repo.get_distinct_years(db),
        "months": cost_repo.get_distinct_months(db, year=query.year),
        "locations": location_service.list_registered(db),
        "suppliers": SupplierService().list_registered_names(db),
        "vehicle_models": VehicleModelService().list_filter_codes(db, query.location),
        "versions": cost_repo.get_distinct_versions(
            db,
            year=query.year,
            month=query.month,
            locations=locations,
            vehicle_model=query.vehicle_model,
        ),
        "summary": cost_repo.summarize_by_filters(
            db,
            year=query.year,
            month=query.month,
            locations=locations,
            stamping_suppliers=supplier_names,
            vehicle_model=query.vehicle_model,
            version=query.version,
            part_number=query.part_number,
            audit_status=query.audit_status,
        ),
    }
    return (
        to_cost_vos(db, rows, blank_repo=blank_repo, steel_repo=steel_repo),
        total,
        filters,
    )


def get_cost_by_id(
    cost_repo: StampingPartCostRepository,
    blank_repo: StampingTailorWeldBlankRepository,
    steel_repo: SteelPriceRepository,
    db: Session,
    cost_id: int,
) -> StampingPartCostVO:
    record = cost_repo.get_by_id(db, cost_id)
    if record is None:
        raise NotFoundException(f"核算记录不存在: id={cost_id}")
    vos = to_cost_vos(db, [record], blank_repo=blank_repo, steel_repo=steel_repo)
    if not vos:
        raise NotFoundException(f"核算记录不存在: id={cost_id}")
    return vos[0]


def list_years(
    cost_repo: StampingPartCostRepository, steel_repo: SteelPriceRepository, db: Session
) -> list[int]:
    years = set(cost_repo.get_distinct_years(db))
    years.update(steel_repo.list_distinct_years(db))
    return sorted(years, reverse=True)


def list_locations(db: Session, year: int | None = None) -> list[str]:
    return LocationService().list_registered(db)


def list_suppliers(
    cost_repo: StampingPartCostRepository,
    db: Session,
    year: int | None = None,
    month: int | None = None,
    location: str | None = None,
) -> list[str]:
    locations: list[str] | None = None
    if location:
        locations = LocationService().expand_for_query(db, location)
        if not locations:
            return []
    return cost_repo.get_distinct_suppliers(db, year=year, month=month, locations=locations)
