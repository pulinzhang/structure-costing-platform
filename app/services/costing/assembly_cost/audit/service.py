"""成品月核价：范围删除 / 审核 / 反审核。

这三步只按年、月、基地、项目取卡，忽略请求里的 view 和 bom_version
（DTO 的 view 默认 finance，不传也会收成树根）。列表和导出仍走原来的筛选。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import display_name
from app.common.timezone import now
from app.repositories.costing.assembly_cost.assembly_cost_repository import (
    AssemblyCostRepository,
)
from app.schemas.dto.assembly_cost_dto import (
    AssemblyCostBatchApproveDTO,
    AssemblyCostBatchDeleteDTO,
    AssemblyCostBatchReverseDTO,
)
from app.schemas.vo.assembly_cost_vo import AssemblyCostBatchResultVO
from app.schemas.vo.user_vo import UserVO


def batch_delete_costs(
    cost_repo: AssemblyCostRepository,
    db: Session,
    dto: AssemblyCostBatchDeleteDTO,
) -> AssemblyCostBatchResultVO:
    location = dto.location.strip()
    vehicle_model = dto.vehicle_model.strip()
    ids = cost_repo.list_ids_by_scope(
        db,
        year=dto.year,
        month=dto.month,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=None,
        view="all",
    )
    skipped = cost_repo.count_approved_by_ids(db, ids)
    count = cost_repo.delete_by_ids(db, ids)
    db.commit()
    message = f"已删除 {count} 条"
    if skipped:
        message += f"，跳过已审核 {skipped} 条"
    return AssemblyCostBatchResultVO(
        affected_count=count,
        skipped_count=skipped,
        message=message,
    )


def batch_approve_costs(
    cost_repo: AssemblyCostRepository,
    db: Session,
    dto: AssemblyCostBatchApproveDTO,
    current_user: UserVO,
) -> AssemblyCostBatchResultVO:
    location = dto.location.strip()
    vehicle_model = dto.vehicle_model.strip()
    ids = cost_repo.list_ids_by_scope(
        db,
        year=dto.year,
        month=dto.month,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=None,
        view="all",
    )
    count = cost_repo.approve_by_ids(
        db,
        ids,
        audited_by=display_name(current_user),
        audited_at=now(),
        audit_remark=dto.audit_remark,
    )
    db.commit()
    return AssemblyCostBatchResultVO(
        affected_count=count,
        skipped_count=0,
        message=f"已审核通过 {count} 条",
    )


def batch_reverse_costs(
    cost_repo: AssemblyCostRepository,
    db: Session,
    dto: AssemblyCostBatchReverseDTO,
    current_user: UserVO,
) -> AssemblyCostBatchResultVO:
    location = dto.location.strip()
    vehicle_model = dto.vehicle_model.strip()
    ids = cost_repo.list_ids_by_scope(
        db,
        year=dto.year,
        month=dto.month,
        location=location,
        vehicle_model=vehicle_model,
        bom_version=None,
        view="all",
    )
    count = cost_repo.reverse_by_ids(
        db,
        ids,
        reverse_audited_by=display_name(current_user),
        reverse_audited_at=now(),
        reverse_audit_remark=dto.reverse_audit_remark,
    )
    db.commit()
    return AssemblyCostBatchResultVO(
        affected_count=count,
        skipped_count=0,
        message=f"已反审核 {count} 条",
    )
