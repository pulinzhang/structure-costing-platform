"""冲压零件：材料规格去重与拼焊子片尺寸。"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.stamping import StampingPart, StampingTailorWeldBlank
from app.repositories.stamping.part.repository import StampingPartRepository
from app.repositories.stamping.part.types import (
    MaterialAsOfIdentity,
    MaterialAsOfRow,
    MaterialSpecRow,
)
from app.schemas.dto.stamping_part_dto import StampingMaterialQuery
from app.schemas.vo.stamping_vo import StampingMaterialResponse, StampingPartListFilterOptions
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.supplier.service import SupplierService
from app.services.masterdata.vehicle_model.service import VehicleModelService


def nonempty_decimals(values: list[Decimal | None]) -> list[Decimal]:
    return [value for value in values if value is not None]


def _sorted_blanks(part: StampingPart) -> list[StampingTailorWeldBlank]:
    return sorted(
        list(part.tailor_weld_blanks or []),
        key=lambda blank: (blank.blank_seq or 0, blank.id or 0),
    )


def material_row_from_part(part: StampingPart) -> StampingMaterialResponse:
    """普通件用主表尺寸；拼焊件用各子片料厚/长/宽（JSON 拼接在 VO）。"""
    blanks = _sorted_blanks(part)
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
    """列出该基地去重后的 基地 + 材料(钢种) + 厚度（含拼焊子片，统计用，无年月）。"""
    loc = location.strip()
    if not loc:
        return []
    return repository.list_material_specs(db, location=loc)


def _part_material_row(
    part: StampingPart, material: str, *, blank_id: int | None, thickness: Decimal | None
) -> MaterialAsOfRow:
    return {
        "part_id": part.id,
        "location": part.location or "",
        "material": material,
        "thickness": thickness,
        "blank_id": blank_id,
    }


def _blank_rows(part: StampingPart) -> list[MaterialAsOfRow]:
    return [
        _part_material_row(
            part,
            (blank.material or ""),
            blank_id=blank.id,
            thickness=blank.thickness,
        )
        for blank in _sorted_blanks(part)
    ]


MaterialOverlay = Callable[
    [Session, Sequence[MaterialAsOfIdentity], int, int],
    dict[int, str],
]

_material_overlay: MaterialOverlay | None = None


def bind_material_overlay(overlay: MaterialOverlay) -> None:
    """启动时绑上材料变更的批量叠切点。没绑定时行上就是工艺列。"""
    global _material_overlay
    _material_overlay = overlay


def _can_overlay_material(part: StampingPart) -> bool:
    """拼焊按子片，不允许材料变更，不叠切点。利废和副产品也不叠。"""
    return not (part.is_tailor_welded or part.is_offal_nested or part.is_scrap_byproduct)


def list_process_materials_as_of(
    repository: StampingPartRepository,
    db: Session,
    *,
    location: str,
    year: int,
    month: int,
    vehicle_model: str | None = None,
) -> tuple[list[MaterialAsOfRow], list[MaterialAsOfIdentity]]:
    """该月工艺列。不叠材料变更。身份只给直接下游自己去叠切点。"""
    loc = location.strip()
    if not loc:
        return [], []
    vehicle = vehicle_model.strip() if vehicle_model else None
    parts = repository.list_in_period_with_blanks(
        db,
        location=loc,
        as_of_year=year,
        as_of_month=month,
        vehicle_model=vehicle,
    )
    identities: list[MaterialAsOfIdentity] = []
    rows: list[MaterialAsOfRow] = []
    for part in parts:
        if _can_overlay_material(part):
            identities.append(
                {
                    "part_id": part.id,
                    "location": part.location or "",
                    "stamping_supplier": part.stamping_supplier or "",
                    "vehicle_model": part.vehicle_model or "",
                    "part_number": part.part_number or "",
                    "material": part.material or "",
                }
            )
        if part.is_tailor_welded:
            rows.append(
                _part_material_row(
                    part, part.material or "", blank_id=None, thickness=part.thickness
                )
            )
            rows.extend(_blank_rows(part))
            continue
        rows.append(
            _part_material_row(part, part.material or "", blank_id=None, thickness=part.thickness)
        )
    return rows, identities


def list_materials_as_of(
    repository: StampingPartRepository,
    db: Session,
    *,
    location: str,
    year: int,
    month: int,
    vehicle_model: str | None = None,
) -> list[MaterialAsOfRow]:
    """该月材料。只给普通件叠已绑定的切点；拼焊子片保持子片列。"""
    rows, identities = list_process_materials_as_of(
        repository,
        db,
        location=location,
        year=year,
        month=month,
        vehicle_model=vehicle_model,
    )
    overlay = _material_overlay
    if overlay is None or not identities:
        return rows
    resolved = overlay(db, identities, year, month)
    overlaid: list[MaterialAsOfRow] = []
    for row in rows:
        material = row["material"]
        if row["blank_id"] is None and row["part_id"] in resolved:
            material = resolved[row["part_id"]]
        overlaid.append({**row, "material": material})
    return overlaid
