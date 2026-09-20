"""模具费结果：工程变更改图抄写 / 回滚删除（只 flush，由调用方 commit）。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_PENDING, audit_create
from app.models.stamping.die_fee import StampingDieFee
from app.repositories.stamping.die.repository import StampingDiePartRepository
from app.repositories.stamping.die_fee.repository import StampingDieFeeRepository
from app.schemas.dto.stamping_die_fee_dto import DieFeeInsertPayload, DieFeeItemPayload
from app.schemas.vo.user_vo import UserVO


@dataclass(slots=True, frozen=True)
class EngineeringChangeDieFeeCloneResult:
    before_id: int
    after_id: int


def clone_revise_for_engineering_change(
    fee_repo: StampingDieFeeRepository,
    die_part_repo: StampingDiePartRepository,
    db: Session,
    *,
    location: str,
    vehicle_model: str,
    old_part_number: str,
    new_part_number: str,
    from_year: int,
    new_die_part_id: int | None,
    current_user: UserVO,
) -> list[EngineeringChangeDieFeeCloneResult]:
    """旧号 year>=生效年的结果抄到新号；绑新布点（若有）。"""
    loc = (location or "").strip()
    vehicle = (vehicle_model or "").strip()
    old_number = (old_part_number or "").strip()
    new_number = (new_part_number or "").strip()
    if not loc or not vehicle or not old_number or not new_number:
        return []
    if old_number == new_number:
        return []
    old_fees = fee_repo.list_by_part_from_year(
        db,
        location=loc,
        vehicle_model=vehicle,
        part_number=old_number,
        from_year=from_year,
    )
    if not old_fees:
        return []

    resolved_die_part_id = new_die_part_id
    new_supplier: str | None = None
    new_version: str | None = None
    if resolved_die_part_id is not None:
        new_die = die_part_repo.get_identity_by_id(db, resolved_die_part_id)
    else:
        new_die = die_part_repo.get_by_location_vehicle_part(
            db, location=loc, vehicle_model=vehicle, part_number=new_number
        )
        if new_die is not None:
            resolved_die_part_id = new_die.id
    if new_die is not None:
        new_supplier = new_die.stamping_supplier
        new_version = new_die.version

    audit = audit_create(current_user)
    results: list[EngineeringChangeDieFeeCloneResult] = []
    for old_fee in old_fees:
        existing = fee_repo.get_by_year_location_vehicle_part(
            db,
            year=old_fee.year,
            location=loc,
            vehicle_model=vehicle,
            part_number=new_number,
        )
        if existing is not None:
            continue
        payload = _clone_fee_payload(
            old_fee,
            new_part_number=new_number,
            new_die_part_id=resolved_die_part_id,
            stamping_supplier=(
                new_supplier if new_supplier is not None else old_fee.stamping_supplier
            ),
            version=new_version if new_version is not None else old_fee.version,
            created_by=str(audit["created_by"] or ""),
            updated_by=str(audit["updated_by"] or ""),
        )
        created = fee_repo.insert_with_items(db, payload)
        results.append(
            EngineeringChangeDieFeeCloneResult(before_id=old_fee.id, after_id=created.id)
        )
    return results


def delete_for_engineering_change_rollback(
    fee_repo: StampingDieFeeRepository,
    db: Session,
    fee_id: int,
) -> None:
    """回滚：按 id 删新主表（级联明细）。"""
    record = fee_repo.get_by_id(db, fee_id)
    if record is None:
        return
    fee_repo.delete_by_id(db, record)


def _clone_fee_payload(
    old_fee: StampingDieFee,
    *,
    new_part_number: str,
    new_die_part_id: int | None,
    stamping_supplier: str | None,
    version: str | None,
    created_by: str,
    updated_by: str,
) -> DieFeeInsertPayload:
    items = [
        DieFeeItemPayload(
            source_die_process_id=None,
            process_seq=item.process_seq,
            process_order=item.process_order,
            process_code=item.process_code,
            estimated_weight_t=Decimal(str(item.estimated_weight_t)),
            alloc_ratio=Decimal(str(item.alloc_ratio)),
            die_sets=item.die_sets,
            unit_price=Decimal(str(item.unit_price)),
            allocation_qty=Decimal(str(item.allocation_qty)),
            price_kind=item.price_kind,
            line_die_fee=Decimal(str(item.line_die_fee)),
            basis_text=item.basis_text,
        )
        for item in (old_fee.items or [])
    ]
    return DieFeeInsertPayload(
        year=old_fee.year,
        location=old_fee.location,
        vehicle_model=old_fee.vehicle_model,
        stamping_supplier=stamping_supplier,
        version=version,
        part_number=new_part_number,
        source_die_part_id=new_die_part_id,
        seq_no=old_fee.seq_no,
        part_name=old_fee.part_name,
        material=old_fee.material,
        thickness=(Decimal(str(old_fee.thickness)) if old_fee.thickness is not None else None),
        part_weight=(
            Decimal(str(old_fee.part_weight)) if old_fee.part_weight is not None else None
        ),
        die_type=old_fee.die_type,
        die_method=old_fee.die_method,
        production_mode=old_fee.production_mode,
        part_grade=old_fee.part_grade,
        excel_filename=old_fee.excel_filename,
        price_kind=old_fee.price_kind,
        unit_price=Decimal(str(old_fee.unit_price)),
        allocation_qty=Decimal(str(old_fee.allocation_qty)),
        die_fee=Decimal(str(old_fee.die_fee)),
        adjustment_amount=(
            Decimal(str(old_fee.adjustment_amount))
            if old_fee.adjustment_amount is not None
            else None
        ),
        final_die_fee=Decimal(str(old_fee.final_die_fee)),
        audit_status=AUDIT_PENDING,
        created_by=created_by,
        updated_by=updated_by,
        items=items,
    )
