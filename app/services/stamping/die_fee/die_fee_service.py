"""冲压年度模具费 CRUD。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import (
    AUDIT_APPROVED,
    AUDIT_PENDING,
    AUDIT_REJECTED,
    audit_update,
    display_name,
)
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.stamping.die_fee_repository import StampingDieFeeRepository
from app.repositories.stamping.stamping_die_repository import StampingDiePartRepository
from app.schemas.dto.stamping_die_fee_dto import (
    DieFeePatch,
    StampingDieFeeBatchApproveDTO,
    StampingDieFeeBatchReverseAuditDTO,
    StampingDieFeeDeleteDTO,
    StampingDieFeeQuery,
    StampingDieFeeUpdateDTO,
)
from app.schemas.vo.stamping_die_fee_vo import (
    DieFeeListFilters,
    StampingDieFeeBatchAuditResultVO,
    StampingDieFeeBatchDeleteResultVO,
    StampingDieFeeFilterVO,
    StampingDieFeeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.die_fee.fee_math import ZERO, resolve_final_die_fee


class StampingDieFeeService:
    def __init__(self) -> None:
        self.fee_repo = StampingDieFeeRepository()
        self.die_repo = StampingDiePartRepository()

    def list_filters(self, db: Session, location: str | None) -> StampingDieFeeFilterVO:
        return StampingDieFeeFilterVO(
            years=self.fee_repo.get_distinct_years(db),
            locations=self.die_repo.list_locations(db),
            vehicle_models=self.die_repo.list_vehicle_models(db, location=location),
        )

    def get_by_id(self, db: Session, fee_id: int) -> StampingDieFeeVO:
        record = self.fee_repo.get_by_id(db, fee_id)
        if record is None:
            raise NotFoundException(f"模具费记录不存在: id={fee_id}")
        return StampingDieFeeVO.model_validate(record)

    def paginate(
        self, db: Session, query: StampingDieFeeQuery
    ) -> tuple[list[StampingDieFeeVO], int, DieFeeListFilters]:
        skip = (query.page - 1) * query.size
        rows, total = self.fee_repo.paginate(
            db,
            year=query.year,
            location=query.location,
            vehicle_model=query.vehicle_model,
            part_number=query.part_number,
            audit_status=query.audit_status,
            only_zero=bool(query.only_zero),
            skip=skip,
            limit=query.size,
        )
        summary = self.fee_repo.summarize_by_filters(
            db,
            year=query.year,
            location=query.location,
            vehicle_model=query.vehicle_model,
            part_number=query.part_number,
            audit_status=query.audit_status,
        )
        filters = DieFeeListFilters(
            year=query.year,
            location=query.location,
            vehicle_model=query.vehicle_model,
            part_number=query.part_number,
            audit_status=query.audit_status,
            only_zero=bool(query.only_zero),
            total_count=summary["total_count"],
            pending_count=summary["pending_count"],
            approved_count=summary["approved_count"],
            zero_count=summary["zero_count"],
            total_fee=summary["total_fee"],
            avg_fee=summary["avg_fee"],
        )
        return [StampingDieFeeVO.model_validate(row) for row in rows], total, filters

    def update_adjustment(
        self,
        db: Session,
        fee_id: int,
        dto: StampingDieFeeUpdateDTO,
        current_user: UserVO,
    ) -> StampingDieFeeVO:
        record = self.fee_repo.get_by_id(db, fee_id)
        if record is None:
            raise NotFoundException(f"模具费记录不存在: id={fee_id}")
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再调整")
        final_fee = resolve_final_die_fee(record.die_fee, dto.adjustment_amount)
        if final_fee < ZERO:
            raise BusinessException("最终模具费不能为负")
        remark = (dto.remark or "").strip() or None
        updated = self.fee_repo.update_fields(
            db,
            fee_id,
            DieFeePatch(
                adjustment_amount=dto.adjustment_amount,
                final_die_fee=final_fee,
                remark=remark,
                updated_by=audit_update(current_user)["updated_by"],
            ),
        )
        if updated is None:
            raise NotFoundException(f"模具费记录不存在: id={fee_id}")
        db.commit()
        db.refresh(updated)
        return StampingDieFeeVO.model_validate(updated)

    def delete_one(self, db: Session, fee_id: int) -> None:
        record = self.fee_repo.get_by_id(db, fee_id)
        if record is None:
            raise NotFoundException(f"模具费记录不存在: id={fee_id}")
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再删除")
        self.fee_repo.delete_by_id(db, record)
        db.commit()

    def delete_scope(
        self, db: Session, dto: StampingDieFeeDeleteDTO
    ) -> StampingDieFeeBatchDeleteResultVO:
        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            statuses=[AUDIT_APPROVED],
        )
        deleted = self.fee_repo.delete_unaudited_by_scope(
            db,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
        )
        db.commit()
        return StampingDieFeeBatchDeleteResultVO(
            deleted_count=deleted,
            skipped_approved_count=skipped,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
        )

    def batch_approve(
        self,
        db: Session,
        dto: StampingDieFeeBatchApproveDTO,
        current_user: UserVO,
    ) -> StampingDieFeeBatchAuditResultVO:
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")
        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            statuses=[AUDIT_APPROVED],
        )
        updated = self.fee_repo.approve_by_scope(
            db,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            audited_by=operator,
            audited_at=now(),
            audit_remark=(dto.audit_remark or "").strip() or None,
            updated_by=operator,
        )
        db.commit()
        return StampingDieFeeBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: StampingDieFeeBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> StampingDieFeeBatchAuditResultVO:
        remark = (dto.reverse_audit_remark or "").strip()
        if not remark:
            raise BusinessException("反审核原因必填")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")
        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            statuses=[AUDIT_PENDING, AUDIT_REJECTED],
        )
        updated = self.fee_repo.reverse_by_scope(
            db,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            reverse_audited_by=operator,
            reverse_audited_at=now(),
            reverse_audit_remark=remark,
            updated_by=operator,
        )
        db.commit()
        return StampingDieFeeBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            year=dto.year,
            location=dto.location,
            vehicle_model=dto.vehicle_model,
        )
