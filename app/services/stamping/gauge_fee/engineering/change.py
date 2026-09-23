"""检具费：工程变更改图抄写 / 回滚删除（只 flush，由调用方 commit）。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.common.audit import audit_create
from app.common.vehicle_model import normalize_vehicle_model
from app.exceptions.base import BusinessException
from app.repositories.stamping.gauge_fee.repository import StampingGaugeFeeRepository
from app.schemas.dto.stamping_gauge_fee_dto import StampingGaugeFeeInsert
from app.schemas.vo.user_vo import UserVO
from app.services.settings.schema_comment.service import ensure_deletable


@dataclass(slots=True, frozen=True)
class EngineeringChangeGaugeFeeCloneResult:
    before_id: int
    after_id: int


def clone_revise_for_engineering_change(
    repository: StampingGaugeFeeRepository,
    db: Session,
    *,
    location: str,
    vehicle_model: str,
    old_part_number: str,
    new_part_number: str,
    current_user: UserVO,
) -> EngineeringChangeGaugeFeeCloneResult | None:
    """旧号有生效档且新号尚无唯一键 → 抄到新号。"""
    loc = (location or "").strip()
    vehicle = normalize_vehicle_model(vehicle_model) or ""
    if not loc or not vehicle:
        raise BusinessException("工程变更抄检具费须选定基地与项目")
    old_number = (old_part_number or "").strip()
    new_number = (new_part_number or "").strip()
    if not old_number or not new_number or old_number == new_number:
        return None
    old_row = repository.get_effective_by_part(
        db, location=loc, vehicle_model=vehicle, part_number=old_number
    )
    if old_row is None:
        return None
    if (
        repository.get_by_part(db, location=loc, vehicle_model=vehicle, part_number=new_number)
        is not None
    ):
        return None
    audit = audit_create(current_user)
    repository.bulk_create(
        db,
        [
            StampingGaugeFeeInsert(
                location=loc,
                vehicle_model=vehicle,
                part_number=new_number,
                part_name=old_row.part_name,
                gauge_fee=Decimal(str(old_row.gauge_fee)),
                allocation_qty=Decimal(str(old_row.allocation_qty)),
                status=old_row.status,
                created_by=str(audit["created_by"] or ""),
                updated_by=str(audit["updated_by"] or ""),
            )
        ],
    )
    new_row = repository.get_by_part(
        db, location=loc, vehicle_model=vehicle, part_number=new_number
    )
    if new_row is None:
        raise BusinessException(f"工程变更抄检具费失败: {new_number}")
    return EngineeringChangeGaugeFeeCloneResult(before_id=old_row.id, after_id=new_row.id)


def delete_for_engineering_change_rollback(
    repository: StampingGaugeFeeRepository,
    db: Session,
    fee_id: int,
) -> None:
    """回滚：按 id 删新行。"""
    record = repository.get_by_id(db, fee_id)
    if record is None:
        return
    ensure_deletable(db, "stamping_gauge_fees", [{"id": record.id}], subject="该检具费")
    repository.delete(db, record)
