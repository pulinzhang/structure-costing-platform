"""年度零件价：工程变更换号抄写 / 回滚删除（只 flush，由调用方 commit）。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.exceptions.base import BusinessException
from app.models.bom.annual_part_price import BomAnnualPartPrice
from app.repositories.bom.annual_part_price_repository import BomAnnualPartPriceRepository
from app.schemas.dto.bom_annual_part_price_dto import BomAnnualPartPriceCreate
from app.schemas.vo.user_vo import UserVO
from app.services.settings.schema_comment.service import ensure_deletable


@dataclass(slots=True, frozen=True)
class EngineeringChangeAnnualPartPriceCloneResult:
    before_id: int
    after_id: int


def clone_revise_for_engineering_change(
    repository: BomAnnualPartPriceRepository,
    db: Session,
    *,
    location: str,
    old_part_number: str,
    new_part_number: str,
    from_year: int,
    current_user: UserVO,
) -> list[EngineeringChangeAnnualPartPriceCloneResult]:
    """旧号 year>=生效年的年度价整行抄到新号（unit_price 照抄，不重算转换）。"""
    loc = (location or "").strip()
    if not loc:
        raise BusinessException("工程变更抄年度零件价须选定基地")
    old_number = (old_part_number or "").strip()
    new_number = (new_part_number or "").strip()
    if not old_number or not new_number or old_number == new_number:
        return []
    old_rows = repository.list_by_part_from_year(
        db,
        location=loc,
        part_number=old_number,
        from_year=from_year,
    )
    if not old_rows:
        return []
    audit = audit_create(current_user)
    results: list[EngineeringChangeAnnualPartPriceCloneResult] = []
    for old_row in old_rows:
        existing = repository.get_by_location_year_part_number(db, loc, old_row.year, new_number)
        if existing is not None:
            continue
        created = repository.create(
            db,
            _clone_create(old_row, loc=loc, new_part_number=new_number),
            created_by=str(audit["created_by"] or ""),
            updated_by=str(audit["updated_by"] or ""),
        )
        results.append(
            EngineeringChangeAnnualPartPriceCloneResult(before_id=old_row.id, after_id=created.id)
        )
    return results


def delete_for_engineering_change_rollback(
    repository: BomAnnualPartPriceRepository,
    db: Session,
    price_id: int,
) -> None:
    """回滚：按 id 删新行（不过审核锁）。"""
    record = repository.get_by_id(db, price_id)
    if record is None:
        return
    ensure_deletable(db, "bom_annual_part_prices", [{"id": record.id}], subject="该年度零件价")
    repository.delete(db, record.id)


def _clone_create(
    old_row: BomAnnualPartPrice,
    *,
    loc: str,
    new_part_number: str,
) -> BomAnnualPartPriceCreate:
    return BomAnnualPartPriceCreate(
        location=loc,
        year=old_row.year,
        part_number=new_part_number,
        part_name=old_row.part_name,
        specification=old_row.specification,
        purchase_unit=old_row.purchase_unit,
        purchase_unit_price=_optional_money(old_row.purchase_unit_price),
        conversion_factor=Decimal(str(old_row.conversion_factor or 1)),
        unit=old_row.unit,
        unit_price=Decimal(str(old_row.unit_price)),
        supply_type=old_row.supply_type,
        supplier_name=old_row.supplier_name,
        remark=old_row.remark,
    )


def _optional_money(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
