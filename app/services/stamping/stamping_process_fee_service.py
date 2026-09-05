"""
冲压加工费 CRUD / 统计服务

列表、其它费用编辑、审核、删除、筛选维度。
计算逻辑见 app.services.stamping.process_fee.calc。
"""

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
from app.repositories.stamping.stamping_process_fee_repository import (
    ProcessFeeListFilters,
    StampingProcessFeeRepository,
)
from app.repositories.stamping.tonnage_price_repository import StampingTonnagePriceRepository
from app.schemas.dto.stamping_process_fee_dto import (
    ProcessFeePatch,
    StampingProcessFeeBatchApproveDTO,
    StampingProcessFeeBatchReverseAuditDTO,
    StampingProcessFeeDeleteDTO,
    StampingProcessFeeQuery,
    StampingProcessFeeUpdateDTO,
)
from app.schemas.vo.stamping_process_fee_vo import (
    StampingProcessFeeBatchAuditResultVO,
    StampingProcessFeeBatchDeleteResultVO,
    StampingProcessFeeVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.stamping.process_fee.fee_math import resolve_final_fee
from app.services.stamping.process_fee.scope import require_scope


class StampingProcessFeeService:
    """冲压加工费 CRUD 与筛选统计。"""

    def __init__(self) -> None:
        self.fee_repo = StampingProcessFeeRepository()
        self.tonnage_repo = StampingTonnagePriceRepository()

    def update_other_fee(
        self,
        db: Session,
        fee_id: int,
        dto: StampingProcessFeeUpdateDTO,
        current_user: UserVO,
    ) -> StampingProcessFeeVO:
        record = self.fee_repo.get_by_id(db, fee_id)
        if not record:
            raise NotFoundException(f"加工费记录不存在: id={fee_id}")
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再调整")

        other_fee = dto.other_fee
        if record.is_tailor_welded and other_fee is None:
            raise BusinessException("拼焊件须录入其它费用（如拼焊费）")
        final_fee = resolve_final_fee(record.processing_fee, other_fee)
        remark = (dto.remark or "").strip() or None
        updated = self.fee_repo.update_fields(
            db,
            fee_id,
            ProcessFeePatch(
                other_fee=other_fee,
                final_processing_fee=final_fee,
                remark=remark,
                updated_by=audit_update(current_user)["updated_by"],
            ),
        )
        if not updated:
            raise NotFoundException(f"加工费记录不存在: id={fee_id}")
        db.commit()
        db.refresh(updated)
        return StampingProcessFeeVO.model_validate(updated)

    def get_by_id(self, db: Session, fee_id: int) -> StampingProcessFeeVO:
        record = self.fee_repo.get_by_id(db, fee_id)
        if not record:
            raise NotFoundException(f"加工费记录不存在: id={fee_id}")
        return StampingProcessFeeVO.model_validate(record)

    def paginate(
        self,
        db: Session,
        query: StampingProcessFeeQuery,
    ) -> tuple[list[StampingProcessFeeVO], int, ProcessFeeListFilters]:
        skip = (query.page - 1) * query.size
        rows, total = self.fee_repo.paginate(
            db,
            year=query.year,
            location=query.location,
            stamping_supplier=query.stamping_supplier,
            vehicle_model=query.vehicle_model,
            version=query.version,
            part_number=query.part_number,
            audit_status=query.audit_status,
            only_zero=bool(query.only_zero),
            skip=skip,
            limit=query.size,
        )
        vos = [StampingProcessFeeVO.model_validate(r) for r in rows]
        # HUD 汇总不含 only_zero，避免点进待办筛选后大盘数字被掏空
        filters: ProcessFeeListFilters = {
            "year": query.year,
            "location": query.location,
            "stamping_supplier": query.stamping_supplier,
            "vehicle_model": query.vehicle_model,
            "version": query.version,
            "part_number": query.part_number,
            "audit_status": query.audit_status,
            "only_zero": bool(query.only_zero),
            "summary": self.fee_repo.summarize_by_filters(
                db,
                year=query.year,
                location=query.location,
                stamping_supplier=query.stamping_supplier,
                vehicle_model=query.vehicle_model,
                version=query.version,
                part_number=query.part_number,
                audit_status=query.audit_status,
            ),
        }
        return vos, total, filters

    def batch_delete(
        self,
        db: Session,
        dto: StampingProcessFeeDeleteDTO,
    ) -> StampingProcessFeeBatchDeleteResultVO:
        scope = require_scope(dto)

        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=scope.year,
            location=scope.location,
            stamping_supplier=scope.stamping_supplier,
            vehicle_model=scope.vehicle_model,
            version=scope.version,
            statuses=[AUDIT_APPROVED],
        )
        deleted = self.fee_repo.delete_unaudited_by_scope(
            db,
            year=scope.year,
            location=scope.location,
            stamping_supplier=scope.stamping_supplier,
            vehicle_model=scope.vehicle_model,
            version=scope.version,
        )
        db.commit()
        return StampingProcessFeeBatchDeleteResultVO(
            deleted_count=deleted,
            skipped_approved_count=skipped,
            year=scope.year,
            location=scope.location,
            stamping_supplier=scope.stamping_supplier,
            vehicle_model=scope.vehicle_model,
            version=scope.version,
        )

    def batch_approve(
        self,
        db: Session,
        dto: StampingProcessFeeBatchApproveDTO,
        current_user: UserVO,
    ) -> StampingProcessFeeBatchAuditResultVO:
        scope = require_scope(dto)
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=scope.year,
            location=scope.location,
            stamping_supplier=scope.stamping_supplier,
            vehicle_model=scope.vehicle_model,
            version=scope.version,
            statuses=[AUDIT_APPROVED],
        )
        missing_other_fee = self.fee_repo.list_tailor_weld_missing_other_fee_part_numbers(
            db,
            year=scope.year,
            location=scope.location,
            stamping_supplier=scope.stamping_supplier,
            vehicle_model=scope.vehicle_model,
            version=scope.version,
            statuses=[AUDIT_PENDING, AUDIT_REJECTED],
        )
        if missing_other_fee:
            preview = "、".join(missing_other_fee[:10])
            extra = f" 等 {len(missing_other_fee)} 件" if len(missing_other_fee) > 10 else ""
            raise BusinessException(f"拼焊件须先录入其它费用（如拼焊费）后再审核：{preview}{extra}")
        updated = self.fee_repo.approve_by_scope(
            db,
            year=scope.year,
            location=scope.location,
            stamping_supplier=scope.stamping_supplier,
            vehicle_model=scope.vehicle_model,
            version=scope.version,
            audited_by=operator,
            audited_at=now(),
            audit_remark=(dto.audit_remark or "").strip() or None,
            updated_by=operator,
        )
        db.commit()
        return StampingProcessFeeBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            year=scope.year,
            location=scope.location,
            stamping_supplier=scope.stamping_supplier,
            vehicle_model=scope.vehicle_model,
            version=scope.version,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: StampingProcessFeeBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> StampingProcessFeeBatchAuditResultVO:
        scope = require_scope(dto)
        remark = (dto.reverse_audit_remark or "").strip()
        if not remark:
            raise BusinessException("反审核原因必填")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=scope.year,
            location=scope.location,
            stamping_supplier=scope.stamping_supplier,
            vehicle_model=scope.vehicle_model,
            version=scope.version,
            statuses=[AUDIT_PENDING, AUDIT_REJECTED],
        )
        updated = self.fee_repo.reverse_by_scope(
            db,
            year=scope.year,
            location=scope.location,
            stamping_supplier=scope.stamping_supplier,
            vehicle_model=scope.vehicle_model,
            version=scope.version,
            reverse_audited_by=operator,
            reverse_audited_at=now(),
            reverse_audit_remark=remark,
            updated_by=operator,
        )
        db.commit()
        return StampingProcessFeeBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            year=scope.year,
            location=scope.location,
            stamping_supplier=scope.stamping_supplier,
            vehicle_model=scope.vehicle_model,
            version=scope.version,
        )

    def list_years(self, db: Session) -> list[int]:
        fee_years = self.fee_repo.get_distinct_years(db)
        rate_years = self.tonnage_repo.get_distinct_years(db)
        return sorted(set(fee_years) | set(rate_years), reverse=True)

    def list_locations(self, db: Session, year: int | None = None) -> list[str]:
        return self.fee_repo.get_distinct_locations(db, year=year)

    def list_suppliers(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
        version: str | None = None,
    ) -> list[str]:
        return self.fee_repo.get_distinct_suppliers(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
            version=version,
        )

    def list_vehicle_models(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
    ) -> list[str]:
        return self.fee_repo.get_distinct_vehicle_models(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
        )

    def list_versions(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        stamping_supplier: str | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        return self.fee_repo.get_distinct_versions(
            db,
            year=year,
            location=location,
            stamping_supplier=stamping_supplier,
            vehicle_model=vehicle_model,
        )
