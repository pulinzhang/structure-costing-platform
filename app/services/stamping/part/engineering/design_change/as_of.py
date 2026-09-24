"""设计变更：当月命中工艺零件，以及工艺还能挂的材料档案字。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.period import is_in_period
from app.repositories.stamping.part.repository import StampingPartRepository
from app.services.stamping.part.engineering.design_change.types import (
    MISS_NOT_AS_OF,
    MISS_SUPPLIER_UNKNOWN,
    EngineeringChangePartAsOfRow,
)


def list_parts_as_of(
    part_repo: StampingPartRepository,
    db: Session,
    *,
    location: str,
    vehicle_model: str,
    as_of_year: int,
    as_of_month: int,
) -> list[EngineeringChangePartAsOfRow]:
    """当月命中的零件号清单（工程变更找旧号 / 避重）。"""
    rows: list[EngineeringChangePartAsOfRow] = []
    for row in part_repo.list_by_location_and_vehicle(
        db, location=location, vehicle_model=vehicle_model
    ):
        if not is_in_period(
            effective_year=row.effective_year,
            effective_month=row.effective_month,
            expiry_year=row.expiry_year,
            expiry_month=row.expiry_month,
            as_of_year=as_of_year,
            as_of_month=as_of_month,
        ):
            continue
        rows.append(
            EngineeringChangePartAsOfRow(
                id=row.id,
                part_number=row.part_number,
                stamping_supplier=(row.stamping_supplier or "").strip(),
                location=row.location or "",
                vehicle_model=row.vehicle_model or "",
                version=row.version or "",
                part_name=row.part_name or "",
                material=row.material,
                thickness=row.thickness,
                effective_year=row.effective_year or 0,
                effective_month=row.effective_month or 0,
                expiry_year=row.expiry_year,
                expiry_month=row.expiry_month,
                is_tailor_welded=bool(row.is_tailor_welded),
                is_offal_nested=bool(row.is_offal_nested),
                is_scrap_byproduct=bool(row.is_scrap_byproduct),
            )
        )
    return rows


def get_part_as_of(
    part_repo: StampingPartRepository,
    db: Session,
    *,
    location: str,
    stamping_supplier: str,
    vehicle_model: str,
    part_number: str,
    as_of_year: int,
    as_of_month: int,
) -> tuple[EngineeringChangePartAsOfRow | None, str | None]:
    """身份四键 + 当月有效。厂名必须是供应商主数据全称。"""
    from app.services.masterdata.supplier.service import SupplierService

    supplier_row = SupplierService().repository.get_by_full_name(db, stamping_supplier)
    if supplier_row is None or supplier_row.full_name != stamping_supplier:
        return None, MISS_SUPPLIER_UNKNOWN
    part = part_repo.get_by_unique_key(
        db,
        location=location,
        stamping_supplier=stamping_supplier,
        vehicle_model=vehicle_model,
        part_number=part_number,
    )
    if part is None:
        return None, MISS_NOT_AS_OF
    if not is_in_period(
        effective_year=part.effective_year,
        effective_month=part.effective_month,
        expiry_year=part.expiry_year,
        expiry_month=part.expiry_month,
        as_of_year=as_of_year,
        as_of_month=as_of_month,
    ):
        return None, MISS_NOT_AS_OF
    return (
        EngineeringChangePartAsOfRow(
            id=part.id,
            part_number=part.part_number,
            stamping_supplier=part.stamping_supplier or "",
            location=part.location or "",
            vehicle_model=part.vehicle_model or "",
            version=part.version or "",
            part_name=part.part_name or "",
            material=part.material,
            thickness=part.thickness,
            effective_year=part.effective_year or 0,
            effective_month=part.effective_month or 0,
            expiry_year=part.expiry_year,
            expiry_month=part.expiry_month,
            is_tailor_welded=bool(part.is_tailor_welded),
            is_offal_nested=bool(part.is_offal_nested),
            is_scrap_byproduct=bool(part.is_scrap_byproduct),
        ),
        None,
    )


def process_material_on_file(db: Session, material: str) -> bool:
    """工艺还能挂的档案字：全等命中 grade。禁止 strip。"""
    from app.services.masterdata.steel_grade_category.service import SteelGradeCategoryService

    if not material:
        return False
    row = SteelGradeCategoryService().repository.get_by_grade(db, material)
    return row is not None and row.grade == material
