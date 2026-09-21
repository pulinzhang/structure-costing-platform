"""冲压零件核价：手工改价与范围审核。"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.costing.stamping_part_cost.stamping_part_cost_repository import (
    StampingPartCostRepository,
)
from app.repositories.costing.steel_price.steel_price_repository import SteelPriceRepository
from app.repositories.stamping.part.tailor_weld_blank import (
    StampingTailorWeldBlankRepository,
)
from app.schemas.dto.stamping_part_cost_dto import (
    StampingPartCostBatchApproveDTO,
    StampingPartCostBatchReverseAuditDTO,
    StampingPartCostDeleteDTO,
    StampingPartCostManualUnitCostDTO,
)
from app.schemas.vo.stamping_part_cost_vo import (
    StampingPartCostBatchAuditResultVO,
    StampingPartCostBatchDeleteResultVO,
    StampingPartCostVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.costing.stamping_part_cost.calc.constants import AMOUNT_QUANTIZE, STATUS_FAILED
from app.services.costing.stamping_part_cost.calc.scope import require_audit_scope, require_scope
from app.services.costing.stamping_part_cost.queries import to_cost_vos


def update_manual_unit_cost(
    cost_repo: StampingPartCostRepository,
    blank_repo: StampingTailorWeldBlankRepository,
    steel_repo: SteelPriceRepository,
    db: Session,
    cost_id: int,
    dto: StampingPartCostManualUnitCostDTO,
    current_user: UserVO,
) -> StampingPartCostVO:
    """仅允许对计算失败且未审核的记录手工录入最终单件成本。"""
    record = cost_repo.get_by_id(db, cost_id)
    if not record:
        raise NotFoundException(f"核算记录不存在: id={cost_id}")
    if record.calc_status != STATUS_FAILED:
        raise BusinessException("仅计算失败的记录允许手工改价")
    if record.audit_status == AUDIT_APPROVED:
        raise BusinessException("已审核通过，请先反审核后再改价")

    remark = (dto.remark or "").strip()
    if not remark:
        raise BusinessException("备注不能为空")

    unit_cost = Decimal(str(dto.unit_cost)).quantize(AMOUNT_QUANTIZE, rounding=ROUND_HALF_UP)
    updated = cost_repo.update_fields(
        db,
        cost_id,
        {
            "unit_cost": unit_cost,
            "remark": remark,
            "updated_by": display_name(current_user),
        },
    )
    if not updated:
        raise NotFoundException(f"核算记录不存在: id={cost_id}")
    db.commit()
    db.refresh(updated)
    vos = to_cost_vos(db, [updated], blank_repo=blank_repo, steel_repo=steel_repo)
    return vos[0]


def batch_delete_costs(
    cost_repo: StampingPartCostRepository,
    db: Session,
    dto: StampingPartCostDeleteDTO,
) -> StampingPartCostBatchDeleteResultVO:
    scope = require_scope(dto)
    skipped = cost_repo.count_by_scope_and_statuses(
        db,
        year=scope.year,
        month=scope.month,
        location=scope.location,
        stamping_supplier=scope.stamping_supplier,
        vehicle_model=scope.vehicle_model,
        version=scope.version,
        statuses=[AUDIT_APPROVED],
    )
    deleted = cost_repo.delete_unaudited_by_scope(
        db,
        year=scope.year,
        month=scope.month,
        location=scope.location,
        stamping_supplier=scope.stamping_supplier,
        vehicle_model=scope.vehicle_model,
        version=scope.version,
    )
    db.commit()
    message = f"已删除 {deleted} 条"
    if skipped:
        message += f"，跳过已审核 {skipped} 条"
    return StampingPartCostBatchDeleteResultVO(
        deleted_count=deleted,
        skipped_approved_count=skipped,
        year=scope.year,
        month=scope.month,
        location=scope.location,
        vehicle_model=scope.vehicle_model,
        version=scope.version,
        stamping_supplier=scope.stamping_supplier,
        message=message,
    )


def batch_approve_costs(
    cost_repo: StampingPartCostRepository,
    db: Session,
    dto: StampingPartCostBatchApproveDTO,
    current_user: UserVO,
) -> StampingPartCostBatchAuditResultVO:
    scope = require_audit_scope(dto)
    updated = cost_repo.approve_by_scope(
        db,
        year=scope.year,
        month=scope.month,
        location=scope.location,
        stamping_supplier=scope.stamping_supplier,
        vehicle_model=scope.vehicle_model,
        version=scope.version,
        audited_by=display_name(current_user),
        audited_at=now(),
        audit_remark=dto.audit_remark,
        updated_by=display_name(current_user),
    )
    skipped = (
        cost_repo.count_by_scope_and_statuses(
            db,
            year=scope.year,
            month=scope.month,
            location=scope.location,
            stamping_supplier=scope.stamping_supplier,
            vehicle_model=scope.vehicle_model,
            version=scope.version,
            statuses=[AUDIT_APPROVED],
        )
        - updated
    )
    db.commit()
    skipped_count = max(skipped, 0)
    message = f"已审核通过 {updated} 条"
    if skipped_count:
        message += f"，跳过 {skipped_count} 条"
    return StampingPartCostBatchAuditResultVO(
        updated_count=updated,
        skipped_count=skipped_count,
        year=scope.year,
        month=scope.month,
        location=scope.location,
        vehicle_model=scope.vehicle_model,
        version=scope.version,
        stamping_supplier=scope.stamping_supplier,
        message=message,
    )


def batch_reverse_audit_costs(
    cost_repo: StampingPartCostRepository,
    db: Session,
    dto: StampingPartCostBatchReverseAuditDTO,
    current_user: UserVO,
) -> StampingPartCostBatchAuditResultVO:
    scope = require_audit_scope(dto)
    updated = cost_repo.reverse_by_scope(
        db,
        year=scope.year,
        month=scope.month,
        location=scope.location,
        stamping_supplier=scope.stamping_supplier,
        vehicle_model=scope.vehicle_model,
        version=scope.version,
        reverse_audited_by=display_name(current_user),
        reverse_audited_at=now(),
        reverse_audit_remark=dto.reverse_audit_remark,
        updated_by=display_name(current_user),
    )
    db.commit()
    return StampingPartCostBatchAuditResultVO(
        updated_count=updated,
        skipped_count=0,
        year=scope.year,
        month=scope.month,
        location=scope.location,
        vehicle_model=scope.vehicle_model,
        version=scope.version,
        stamping_supplier=scope.stamping_supplier,
        message=f"已反审核 {updated} 条",
    )
