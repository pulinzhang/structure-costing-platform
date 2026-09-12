"""冲压零件：材料规格去重与拼焊子片尺寸。"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.stamping import StampingPart
from app.repositories.stamping.stamping_part_repository import MaterialSpecRow
from app.repositories.stamping.stamping_repository import StampingPartRepository
from app.schemas.dto.stamping_part_dto import StampingMaterialQuery
from app.schemas.vo.stamping_vo import StampingMaterialResponse, StampingPartListFilterOptions
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.supplier import SupplierService
from app.services.masterdata.vehicle_model import VehicleModelService


def nonempty_decimals(values: list[Decimal | None]) -> list[Decimal]:
    return [value for value in values if value is not None]


def material_row_from_part(part: StampingPart) -> StampingMaterialResponse:
    """普通件用主表尺寸；拼焊件用各子片料厚/长/宽（JSON 拼接在 VO）。"""
    blanks = sorted(
        list(part.tailor_weld_blanks or []),
        key=lambda blank: (blank.blank_seq or 0, blank.id or 0),
    )
    material = (part.material or "").strip() or None
    if part.is_tailor_welded and len(blanks) >= 2:
        if not material:
            material = (blanks[0].material or "").strip() or None
        return StampingMaterialResponse(
            material=material,
            thickness=nonempty_decimals([blank.thickness for blank in blanks]),
            sheet_length=nonempty_decimals([blank.sheet_length for blank in blanks]),
            sheet_width=nonempty_decimals([blank.sheet_width for blank in blanks]),
        )
    return StampingMaterialResponse(
        material=material,
        thickness=nonempty_decimals([part.thickness]),
        sheet_length=nonempty_decimals([part.sheet_length]),
        sheet_width=nonempty_decimals([part.sheet_width]),
    )


def list_materials(
    repository: StampingPartRepository,
    db: Session,
    query: StampingMaterialQuery,
) -> tuple[list[StampingMaterialResponse], int, StampingPartListFilterOptions]:
    """获取材料列表（去重；拼焊件厚度/长/宽为子片拼接）。"""
    skip = (query.page - 1) * query.size
    location_service = LocationService()
    locations: list[str] | None = None
    if query.location:
        locations = location_service.expand_for_query(db, query.location)
        if not locations:
            filter_vo = StampingPartListFilterOptions(
                locations=location_service.list_registered(db),
                vehicle_models=[],
                versions=[],
                materials=[],
                stamping_suppliers=SupplierService().list_registered_names(db),
            )
            return [], 0, filter_vo
    supplier_names = SupplierService().names_for_query(db, query.stamping_supplier)
    if supplier_names is not None and not supplier_names:
        filter_vo = StampingPartListFilterOptions(
            locations=location_service.list_registered(db),
            vehicle_models=[],
            versions=[],
            materials=[],
            stamping_suppliers=SupplierService().list_registered_names(db),
        )
        return [], 0, filter_vo
    parts = repository.list_parts_for_materials(
        db,
        locations=locations,
        stamping_suppliers=supplier_names,
        vehicle_model=query.vehicle_model,
        version=query.version,
    )

    unique_rows: list[StampingMaterialResponse] = []
    seen: set[tuple[str | None, tuple[Decimal, ...], tuple[Decimal, ...], tuple[Decimal, ...]]] = (
        set()
    )
    for part in parts:
        row = material_row_from_part(part)
        key = (
            row.material,
            tuple(row.thickness),
            tuple(row.sheet_length),
            tuple(row.sheet_width),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)

    unique_rows.sort(
        key=lambda row: (
            row.material or "",
            tuple(row.thickness),
            tuple(row.sheet_length),
            tuple(row.sheet_width),
        )
    )
    total = len(unique_rows)
    page_rows = unique_rows[skip : skip + query.size]
    filter_options = repository.get_filter_options(db)
    filter_vo = StampingPartListFilterOptions(
        locations=location_service.list_registered(db),
        vehicle_models=VehicleModelService().list_filter_codes(db, query.location),
        versions=list(filter_options["versions"]),
        materials=list(filter_options["materials"]),
        stamping_suppliers=SupplierService().list_registered_names(db),
    )
    return page_rows, total, filter_vo


def count_material_specs(
    repository: StampingPartRepository,
    db: Session,
    *,
    location: str | None = None,
    vehicle_model: str | None = None,
) -> int:
    """统计去重后的材料+厚度规格行数（含拼焊子片；统计可按车型收窄）。"""
    loc = location.strip() if location else None
    vehicle = vehicle_model.strip() if vehicle_model else None
    if not loc and not vehicle:
        return 0
    return repository.count_material_specs(
        db,
        location=loc,
        vehicle_model=vehicle,
    )


def list_distinct_spec_grades(
    repository: StampingPartRepository,
    db: Session,
    *,
    location: str | None = None,
    vehicle_model: str | None = None,
) -> list[str]:
    """统计用：范围内去重牌号（含拼焊子片）。"""
    loc = location.strip() if location else None
    vehicle = vehicle_model.strip() if vehicle_model else None
    if not loc and not vehicle:
        return []
    return repository.list_distinct_spec_grades(
        db,
        location=loc,
        vehicle_model=vehicle,
    )


def list_material_specs(
    repository: StampingPartRepository, db: Session, *, location: str
) -> list[MaterialSpecRow]:
    """列出该基地去重后的 基地 + 材料(钢种) + 厚度（含拼焊子片，钢价计算用）。"""
    loc = location.strip()
    if not loc:
        return []
    return repository.list_material_specs(db, location=loc)
