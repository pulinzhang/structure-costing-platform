"""
BOM 焊接费 CRUD / 审核 / 删除服务
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.common.audit import (
    AUDIT_APPROVED,
    AUDIT_PENDING,
    AUDIT_REJECTED,
    display_name,
    audit_update,
)
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom import BomL0WeldingFee
from app.repositories.bom.l0_welding_fee_repository import (
    BomL0WeldingFeeRepository,
    L0WeldingFeeListFilters,
)
from app.services.bom.l0_welding_fee.fee_math import resolve_final_l0_welding_fee
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.dto.bom_l0_welding_fee_dto import (
    BomL0WeldingFeeBatchApproveDTO,
    BomL0WeldingFeeBatchDeleteDTO,
    BomL0WeldingFeeBatchReverseAuditDTO,
    BomL0WeldingFeeQuery,
    BomL0WeldingFeeUpdateDTO,
    L0WeldingFeePatch,
)
from app.schemas.vo.bom_l0_welding_fee_vo import (
    BomL0WeldingFeeBatchAuditResultVO,
    BomL0WeldingFeeBatchDeleteResultVO,
    BomL0WeldingFeeVO,
)
from app.schemas.vo.user_vo import UserVO


def _normalize_scope(
    *,
    location: str,
    vehicle_model: str,
    bom_version: str,
) -> tuple[str, str, str]:
    return location.strip(), vehicle_model.strip(), bom_version.strip()


class BomL0WeldingFeeService:
    """焊接费列表、详情、批量审核与删除。"""

    def __init__(self) -> None:
        self.fee_repo = BomL0WeldingFeeRepository()
        self.breakdown_repo = BomWeldingProcessBreakdownRepository()

    def update_other_fee(
        self,
        db: Session,
        fee_id: int,
        dto: BomL0WeldingFeeUpdateDTO,
        current_user: UserVO,
    ) -> BomL0WeldingFeeVO:
        record = self.fee_repo.get_by_id(db, fee_id)
        if not record:
            raise NotFoundException(f"成品焊接费记录不存在: id={fee_id}")
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再调整")

        other_fee = dto.other_fee
        final_fee = resolve_final_l0_welding_fee(
            record.total_l0_welding_fee,
            other_fee,
        )
        remark = (dto.remark or "").strip() or None
        updated = self.fee_repo.update_fields(
            db,
            fee_id,
            L0WeldingFeePatch(
                other_fee=other_fee,
                final_l0_welding_fee=final_fee,
                remark=remark,
                updated_by=audit_update(current_user)["updated_by"],
            ),
        )
        if not updated:
            raise NotFoundException(f"成品焊接费记录不存在: id={fee_id}")
        db.commit()
        db.refresh(updated)
        return self._to_vo(db, updated)

    def get_by_id(self, db: Session, fee_id: int) -> BomL0WeldingFeeVO:
        record = self.fee_repo.get_by_id(db, fee_id)
        if not record:
            raise NotFoundException(f"成品焊接费记录不存在: id={fee_id}")
        return self._to_vo(db, record)

    def list_fees(
        self,
        db: Session,
        query: BomL0WeldingFeeQuery,
    ) -> tuple[list[BomL0WeldingFeeVO], int, L0WeldingFeeListFilters]:
        skip = (query.page - 1) * query.size
        rows, total = self.fee_repo.paginate(
            db,
            year=query.year,
            location=query.location,
            vehicle_model=query.vehicle_model,
            bom_version=query.bom_version,
            part_number=query.part_number,
            audit_status=query.audit_status,
            calc_status=query.calc_status,
            skip=skip,
            limit=query.size,
        )
        vos = self._to_vos(db, rows)
        filters: L0WeldingFeeListFilters = {
            "year": query.year,
            "location": query.location,
            "vehicle_model": query.vehicle_model,
            "bom_version": query.bom_version,
            "part_number": query.part_number,
            "audit_status": query.audit_status,
            "calc_status": query.calc_status,
            "summary": self.fee_repo.summarize_by_filters(
                db,
                year=query.year,
                location=query.location,
                vehicle_model=query.vehicle_model,
                bom_version=query.bom_version,
                part_number=query.part_number,
                audit_status=query.audit_status,
                calc_status=query.calc_status,
            ),
        }
        return vos, total, filters

    def _to_vo(self, db: Session, record: BomL0WeldingFee) -> BomL0WeldingFeeVO:
        return self._to_vos(db, [record])[0]

    def _to_vos(self, db: Session, records: list[BomL0WeldingFee]) -> list[BomL0WeldingFeeVO]:
        need_ids = [
            int(r.source_breakdown_node_id)
            for r in records
            if r.source_breakdown_node_id and not (r.weld_info_raw or "").strip()
        ]
        weld_map = self.breakdown_repo.map_weld_info_by_ids(db, need_ids) if need_ids else {}
        result: list[BomL0WeldingFeeVO] = []
        for record in records:
            vo = BomL0WeldingFeeVO.model_validate(record)
            if not (vo.weld_info_raw or "").strip() and record.source_breakdown_node_id:
                fallback = weld_map.get(int(record.source_breakdown_node_id))
                if fallback:
                    vo.weld_info_raw = fallback
            result.append(vo)
        return result

    def batch_delete(
        self,
        db: Session,
        dto: BomL0WeldingFeeBatchDeleteDTO,
    ) -> BomL0WeldingFeeBatchDeleteResultVO:
        location, vehicle_model, bom_version = _normalize_scope(
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            bom_version=dto.bom_version,
        )
        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            statuses=[AUDIT_APPROVED],
        )
        deleted = self.fee_repo.delete_unaudited_by_scope(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )
        db.commit()
        return BomL0WeldingFeeBatchDeleteResultVO(
            deleted_count=deleted,
            skipped_approved_count=skipped,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def batch_approve(
        self,
        db: Session,
        dto: BomL0WeldingFeeBatchApproveDTO,
        current_user: UserVO,
    ) -> BomL0WeldingFeeBatchAuditResultVO:
        location, vehicle_model, bom_version = _normalize_scope(
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            bom_version=dto.bom_version,
        )
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            statuses=[AUDIT_APPROVED],
        )
        updated = self.fee_repo.approve_by_scope(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            audited_by=operator,
            audited_at=now(),
            audit_remark=(dto.audit_remark or "").strip() or None,
            updated_by=operator,
        )
        db.commit()
        return BomL0WeldingFeeBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: BomL0WeldingFeeBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> BomL0WeldingFeeBatchAuditResultVO:
        location, vehicle_model, bom_version = _normalize_scope(
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            bom_version=dto.bom_version,
        )
        remark = (dto.reverse_audit_remark or "").strip()
        if not remark:
            raise BusinessException("反审核原因必填")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            statuses=[AUDIT_PENDING, AUDIT_REJECTED],
        )
        updated = self.fee_repo.reverse_by_scope(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
            reverse_audited_by=operator,
            reverse_audited_at=now(),
            reverse_audit_remark=remark,
            updated_by=operator,
        )
        db.commit()
        return BomL0WeldingFeeBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            bom_version=bom_version,
        )

    def list_years(self, db: Session) -> list[int]:
        return self.fee_repo.get_distinct_years(db)

    def list_locations(self, db: Session, year: int | None = None) -> list[str]:
        return self.fee_repo.get_distinct_locations(db, year=year)

    def list_vehicle_models(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
    ) -> list[str]:
        return self.fee_repo.get_distinct_vehicle_models(db, year=year, location=location)

    def list_bom_versions(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        return self.fee_repo.get_distinct_bom_versions(
            db,
            year=year,
            location=location,
            vehicle_model=vehicle_model,
        )
