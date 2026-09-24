"""冲压零件：列表、级联筛与主数据汇总。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.period import resolve_as_of_month
from app.exceptions import NotFoundException
from app.repositories.stamping.part.process import StampingProcessRepository
from app.repositories.stamping.part.repository import StampingPartRepository
from app.schemas.dto.stamping_part_dto import StampingCascadeFilterQuery, StampingPartQuery
from app.schemas.vo.stamping_vo import (
    StampingCascadeFilterOptionsVO,
    StampingPartListFilterOptions,
    StampingPartListResponse,
    StampingPartListSummaryVO,
    StampingPartWithProcessesResponse,
)
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.supplier.service import SupplierService
from app.services.masterdata.vehicle_model.service import VehicleModelService
from app.services.stamping.part.engineering.material_change import material_changes_for_detail


def count_parts(repository: StampingPartRepository, db: Session) -> int:
    return repository.count_all(db)


def count_processes(process_repository: StampingProcessRepository, db: Session) -> int:
    return process_repository.count_all(db)


def count_vehicle_models(repository: StampingPartRepository, db: Session) -> int:
    return repository.count_distinct_vehicle_models(db)


def summarize_master(
    repository: StampingPartRepository,
    process_repository: StampingProcessRepository,
    db: Session,
    *,
    location: str | None = None,
    vehicle_model: str | None = None,
) -> dict[str, int]:
    """按基地 / 车型汇总主数据：零件数 / 工序数 / 车型数。"""
    location_clean = location.strip() if location else None
    vehicle_clean = vehicle_model.strip() if vehicle_model else None
    locations: list[str] | None = None
    if location_clean:
        locations = LocationService().expand_for_query(db, location_clean)
        if not locations:
            return {"parts": 0, "processes": 0, "models": 0}
    _rows, parts = repository.paginate(
        db,
        locations=locations,
        vehicle_model=vehicle_clean,
        skip=0,
        limit=1,
    )
    summary = repository.summarize_by_filters(
        db,
        locations=locations,
        vehicle_model=vehicle_clean,
    )
    return {
        "parts": int(parts),
        "processes": process_repository.count_by_part_location(
            db,
            location_clean,
            vehicle_clean,
        ),
        "models": int(summary.get("vehicle_model_count") or 0),
    }


def _empty_list_filters(
    db: Session,
    location_service: LocationService,
    location: str | None,
) -> StampingPartListFilterOptions:
    raw = StampingPartRepository().get_filter_options(db)
    return StampingPartListFilterOptions(
        locations=location_service.list_registered(db),
        vehicle_models=VehicleModelService().list_filter_codes(db, location),
        versions=list(raw["versions"]),
        materials=list(raw["materials"]),
        stamping_suppliers=SupplierService().list_registered_names(db),
        summary=StampingPartListSummaryVO(),
    )


def list_parts(
    repository: StampingPartRepository,
    db: Session,
    query: StampingPartQuery,
) -> tuple[list[StampingPartListResponse], int, StampingPartListFilterOptions]:
    """获取零件列表（不含工序详情，含工序统计数 process_count）"""
    skip = (query.page - 1) * query.size
    location_service = LocationService()
    locations: list[str] | None = None
    if query.location:
        locations = location_service.expand_for_query(db, query.location)
        if not locations:
            return [], 0, _empty_list_filters(db, location_service, query.location)
    supplier_names = SupplierService().names_for_query(db, query.stamping_supplier)
    if supplier_names is not None and not supplier_names:
        return [], 0, _empty_list_filters(db, location_service, query.location)
    vehicle_model = query.vehicle_model
    version = query.version
    part_number = query.part_number
    part_name = query.part_name
    as_of_year, as_of_month = resolve_as_of_month(query.year, query.month)
    parts, total = repository.paginate(
        db,
        locations=locations,
        vehicle_model=vehicle_model,
        version=version,
        part_number=part_number,
        part_name=part_name,
        stamping_suppliers=supplier_names,
        skip=skip,
        limit=query.size,
        as_of_year=as_of_year,
        as_of_month=as_of_month,
        include_expired=query.include_expired,
    )
    # 一次聚合查询补齐每行工序数（避免 ORM lazy load 触发 N+1）
    part_ids = [p.id for p in parts]
    process_counts = repository.count_processes_by_part_ids(db, part_ids)

    rows = []
    for p in parts:
        row = StampingPartListResponse.model_validate(p)
        row.process_count = process_counts.get(p.id, 0)
        rows.append(row)

    raw = repository.get_filter_options(db)
    filter_vo = StampingPartListFilterOptions(
        locations=location_service.list_registered(db),
        vehicle_models=VehicleModelService().list_filter_codes(db, query.location),
        versions=list(raw["versions"]),
        materials=list(raw["materials"]),
        stamping_suppliers=SupplierService().list_registered_names(db),
        summary=StampingPartListSummaryVO.model_validate(
            repository.summarize_by_filters(
                db,
                locations=locations,
                vehicle_model=vehicle_model,
                version=version,
                part_number=part_number,
                part_name=part_name,
                stamping_suppliers=supplier_names,
            )
        ),
    )
    return rows, total, filter_vo


def get_filter_options(
    repository: StampingPartRepository, db: Session
) -> StampingPartListFilterOptions:
    raw = repository.get_filter_options(db)
    return StampingPartListFilterOptions(
        locations=LocationService().list_registered(db),
        vehicle_models=VehicleModelService().list_filter_codes(db),
        versions=list(raw["versions"]),
        materials=list(raw["materials"]),
        stamping_suppliers=SupplierService().list_registered_names(db),
        summary=StampingPartListSummaryVO(),
    )


def get_cascade_filter_options(
    repository: StampingPartRepository,
    db: Session,
    query: StampingCascadeFilterQuery,
) -> StampingCascadeFilterOptionsVO:
    """获取基地 → 项目 → 版本 → 冲压工厂 级联筛选选项"""
    location_service = LocationService()
    location_raw = query.location.strip() if query.location else None
    locations: list[str] | None = None
    if location_raw:
        locations = location_service.expand_for_query(db, location_raw)
        if not locations:
            return StampingCascadeFilterOptionsVO(
                locations=location_service.list_enabled(db),
                stamping_suppliers=[],
                vehicle_models=[],
                versions=[],
            )
    raw = repository.get_cascade_filter_options(
        db,
        locations=locations,
        stamping_supplier=query.stamping_supplier.strip() if query.stamping_supplier else None,
        vehicle_model=query.vehicle_model.strip() if query.vehicle_model else None,
        version=query.version.strip() if query.version else None,
        overlap_year=(query.year if query.year is not None and query.month is None else None),
    )
    vehicle_svc = VehicleModelService()
    if location_raw and query.year is not None and query.month is not None:
        vehicle_models = vehicle_svc.list_introducible(db, location_raw, query.year, query.month)
    elif query.year is not None and query.month is None:
        overlapping = (
            set(vehicle_svc.list_overlaps_year(db, location_raw, query.year))
            if location_raw
            else set()
        )
        vehicle_models = [code for code in raw["vehicle_models"] if code in overlapping]
    else:
        vehicle_models = vehicle_svc.list_filter_codes(db, location_raw)
    return StampingCascadeFilterOptionsVO(
        locations=location_service.list_enabled(db),
        stamping_suppliers=list(raw["stamping_suppliers"]),
        vehicle_models=vehicle_models,
        versions=list(raw["versions"]),
    )


def get_by_id(
    repository: StampingPartRepository, db: Session, part_id: int
) -> StampingPartWithProcessesResponse:
    part = repository.get_by_id(db, part_id)
    if not part:
        raise NotFoundException(f"零件不存在: id={part_id}")
    detail = StampingPartWithProcessesResponse.model_validate(part)
    detail.material_changes = material_changes_for_detail(db, part.id)
    return detail
