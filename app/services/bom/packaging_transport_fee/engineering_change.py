"""包装运输费：工程变更种新树抄写 / 回滚删除（只 flush，由调用方 commit）。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException
from app.models.bom.packaging_transport_fee import BomPackagingTransportFee
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
)
from app.schemas.dto.bom_packaging_transport_fee_dto import BomPackagingTransportFeeCreate
from app.schemas.vo.user_vo import UserVO


@dataclass(slots=True, frozen=True)
class EngineeringChangePackagingFeeCloneResult:
    before_id: int
    after_id: int


def clone_revise_for_engineering_change(
    repository: BomPackagingTransportFeeRepository,
    db: Session,
    *,
    location: str,
    vehicle_model: str,
    old_part_number: str,
    new_part_number: str,
    from_year: int,
    current_user: UserVO,
) -> list[EngineeringChangePackagingFeeCloneResult]:
    """旧交货总成 year>=生效年的包装行抄到新总成。"""
    loc = (location or "").strip()
    vehicle = normalize_vehicle_model(vehicle_model) or ""
    if not loc or not vehicle:
        raise BusinessException("工程变更抄包装运输费须选定基地与项目")
    old_number = (old_part_number or "").strip()
    new_number = (new_part_number or "").strip()
    if not old_number or not new_number or old_number == new_number:
        return []
    old_rows = repository.list_by_part_from_year(
        db,
        location=loc,
        vehicle_model=vehicle,
        part_number=old_number,
        from_year=from_year,
    )
    if not old_rows:
        return []
    audit = audit_create(current_user)
    results: list[EngineeringChangePackagingFeeCloneResult] = []
    for old_row in old_rows:
        existing = repository.get_by_unique_key(
            db,
            location=loc,
            year=old_row.year,
            vehicle_model=vehicle,
            part_number=new_number,
        )
        if existing is not None:
            continue
        created = repository.create(
            db,
            _clone_create(old_row, loc=loc, vehicle=vehicle, new_part_number=new_number),
            created_by=str(audit["created_by"] or ""),
            updated_by=str(audit["updated_by"] or ""),
        )
        results.append(
            EngineeringChangePackagingFeeCloneResult(before_id=old_row.id, after_id=created.id)
        )
    return results


def delete_for_engineering_change_rollback(
    repository: BomPackagingTransportFeeRepository,
    db: Session,
    fee_id: int,
) -> None:
    """回滚：按 id 删新行（不过审核锁）。"""
    record = repository.get_by_id(db, fee_id)
    if record is None:
        return
    repository.delete(db, record.id)


def _clone_create(
    old_row: BomPackagingTransportFee,
    *,
    loc: str,
    vehicle: str,
    new_part_number: str,
) -> BomPackagingTransportFeeCreate:
    return BomPackagingTransportFeeCreate(
        location=loc,
        year=old_row.year,
        vehicle_model=vehicle,
        part_number=new_part_number,
        part_name=old_row.part_name,
        packaging_type=old_row.packaging_type,
        pieces_per_pack=old_row.pieces_per_pack,
        fixture_length_mm=old_row.fixture_length_mm,
        fixture_width_mm=old_row.fixture_width_mm,
        fixture_height_mm=old_row.fixture_height_mm,
        oem_stock_qty=old_row.oem_stock_qty,
        transit_qty=old_row.transit_qty,
        company_stock_qty=old_row.company_stock_qty,
        total_fixture_qty=old_row.total_fixture_qty,
        fixture_unit_price=_optional_money(old_row.fixture_unit_price),
        fixture_invest_amount=_optional_money(old_row.fixture_invest_amount),
        unit_packaging_fee=Decimal(str(old_row.unit_packaging_fee)),
        round_trip_transport_price=_optional_money(old_row.round_trip_transport_price),
        unit_transport_fee=Decimal(str(old_row.unit_transport_fee)),
        fixture_maint_fee=Decimal(str(old_row.fixture_maint_fee)),
        other_fee=Decimal(str(old_row.other_fee or 0)),
        packaging_transport_total=Decimal(str(old_row.packaging_transport_total)),
        remark=old_row.remark,
        excel_filename=None,
        sheet_name=None,
        excel_row=None,
    )


def _optional_money(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
