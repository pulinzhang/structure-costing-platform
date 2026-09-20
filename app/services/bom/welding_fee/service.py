"""
BOM 焊接费 CRUD / 审核 / 删除服务
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
from app.models.bom import BomWeldingFee
from app.repositories.bom.welding_fee_repository import BomWeldingFeeRepository
from app.repositories.bom.welding_process_breakdown_repository import (
    BomWeldingProcessBreakdownRepository,
)
from app.schemas.dto.bom_welding_fee_dto import (
    BomWeldingFeeBatchApproveDTO,
    BomWeldingFeeBatchDeleteDTO,
    BomWeldingFeeBatchReverseAuditDTO,
    BomWeldingFeeQuery,
    BomWeldingFeeUpdateDTO,
    WeldingFeePatch,
    resolve_welding_fee_levels,
)
from app.schemas.vo.bom_welding_fee_vo import (
    BomWeldingFeeBatchAuditResultVO,
    BomWeldingFeeBatchDeleteResultVO,
    BomWeldingFeeVO,
    WeldingFeeListApiFilters,
    WeldingFeeListSummaryVO,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.bom.period import BomPeriodService
from app.services.bom.welding_fee.fee_math import resolve_final_welding_fee
from app.services.masterdata.location.location_service import LocationService
from app.services.masterdata.vehicle_model.vehicle_model_service import VehicleModelService


def _fee_tree_root_versions(db: Session, records: list[BomWeldingFee]) -> dict[int, str]:
    breakdown_ids = [
        int(record.source_breakdown_node_id)
        for record in records
        if record.source_breakdown_node_id
    ]
    if not breakdown_ids:
        return {}
    nodes = BomWeldingProcessBreakdownRepository().list_nodes_by_ids(db, breakdown_ids)
    by_breakdown = {int(node.id): node for node in nodes}
    by_source = BomPeriodService().map_tree_root_version_by_node_id(
        db,
        [int(node.source_node_id) for node in nodes if node.source_node_id],
    )
    result: dict[int, str] = {}
    for record in records:
        if not record.source_breakdown_node_id:
            continue
        breakdown = by_breakdown.get(int(record.source_breakdown_node_id))
        if breakdown is None or not breakdown.source_node_id:
            continue
        overlay = by_source.get(int(breakdown.source_node_id))
        if overlay:
            result[int(record.id)] = overlay
    return result


def _normalize_scope(
    *,
    location: str,
    vehicle_model: str,
    bom_version: str | None = None,
) -> tuple[str, str, str | None]:
    version = (bom_version or "").strip() or None
    return location.strip(), vehicle_model.strip(), version


class BomWeldingFeeService:
    """焊接费列表、详情、批量审核与删除。"""

    def __init__(self) -> None:
        self.fee_repo = BomWeldingFeeRepository()
        self.breakdown_repo = BomWeldingProcessBreakdownRepository()

    def update_other_fee(
        self,
        db: Session,
        fee_id: int,
        dto: BomWeldingFeeUpdateDTO,
        current_user: UserVO,
    ) -> BomWeldingFeeVO:
        record = self.fee_repo.get_by_id(db, fee_id)
        if not record:
            raise NotFoundException(f"焊接费记录不存在: id={fee_id}")
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再调整")

        other_fee = dto.other_fee
        final_fee = resolve_final_welding_fee(
            record.total_welding_fee,
            other_fee,
        )
        remark = (dto.remark or "").strip() or None
        updated = self.fee_repo.update_fields(
            db,
            fee_id,
            WeldingFeePatch(
                other_fee=other_fee,
                final_welding_fee=final_fee,
                remark=remark,
                updated_by=audit_update(current_user)["updated_by"],
            ),
        )
        if not updated:
            raise NotFoundException(f"焊接费记录不存在: id={fee_id}")
        db.commit()
        db.refresh(updated)
        return self._to_vo(db, updated)

    def get_by_id(self, db: Session, fee_id: int) -> BomWeldingFeeVO:
        record = self.fee_repo.get_by_id(db, fee_id)
        if not record:
            raise NotFoundException(f"焊接费记录不存在: id={fee_id}")
        return self._to_vo(db, record)

    def list_fees(
        self,
        db: Session,
        query: BomWeldingFeeQuery,
    ) -> tuple[list[BomWeldingFeeVO], int, WeldingFeeListApiFilters]:
        skip = (query.page - 1) * query.size
        levels = resolve_welding_fee_levels(level=query.level, levels=query.levels)
        locations: list[str] | None = None
        if query.location:
            locations = LocationService().expand_for_query(db, query.location)
            if not locations:
                summary = WeldingFeeListSummaryVO()
                empty_filters = WeldingFeeListApiFilters(
                    year=query.year,
                    location=query.location,
                    vehicle_model=query.vehicle_model,
                    bom_version=query.bom_version,
                    part_number=query.part_number,
                    audit_status=query.audit_status,
                    calc_status=query.calc_status,
                    level=query.level,
                    levels=levels,
                    summary=summary,
                )
                return [], 0, empty_filters
        source_node_ids = BomPeriodService().node_ids_for_l0_version(
            db,
            bom_version=query.bom_version,
            locations=locations,
            vehicle_model=query.vehicle_model,
        )
        rows, total = self.fee_repo.paginate(
            db,
            year=query.year,
            locations=locations,
            vehicle_model=query.vehicle_model,
            source_node_ids=source_node_ids,
            part_number=query.part_number,
            audit_status=query.audit_status,
            calc_status=query.calc_status,
            levels=levels,
            skip=skip,
            limit=query.size,
        )
        vos = self._to_vos(db, rows)
        # HUD 不含 calc_status，避免点「缺单价待办」后大盘被掏空
        summary = WeldingFeeListSummaryVO.model_validate(
            self.fee_repo.summarize_by_filters(
                db,
                year=query.year,
                locations=locations,
                vehicle_model=query.vehicle_model,
                source_node_ids=source_node_ids,
                part_number=query.part_number,
                audit_status=query.audit_status,
                levels=levels,
            )
        )
        filters: WeldingFeeListApiFilters = {
            "year": query.year,
            "location": query.location,
            "vehicle_model": query.vehicle_model,
            "bom_version": query.bom_version,
            "part_number": query.part_number,
            "audit_status": query.audit_status,
            "calc_status": query.calc_status,
            "level": query.level,
            "levels": levels,
            "summary": summary,
        }
        return vos, total, filters

    def _to_vo(self, db: Session, record: BomWeldingFee) -> BomWeldingFeeVO:
        return self._to_vos(db, [record])[0]

    def _to_vos(self, db: Session, records: list[BomWeldingFee]) -> list[BomWeldingFeeVO]:
        need_ids = [
            int(r.source_breakdown_node_id)
            for r in records
            if r.source_breakdown_node_id and not (r.weld_info_raw or "").strip()
        ]
        weld_map = self.breakdown_repo.map_weld_info_by_ids(db, need_ids) if need_ids else {}
        versions = _fee_tree_root_versions(db, records)
        result: list[BomWeldingFeeVO] = []
        for record in records:
            vo = BomWeldingFeeVO.model_validate(record)
            overlay = versions.get(int(record.id))
            if overlay:
                vo.bom_version = overlay
            if not (vo.weld_info_raw or "").strip() and record.source_breakdown_node_id:
                fallback = weld_map.get(int(record.source_breakdown_node_id))
                if fallback:
                    vo.weld_info_raw = fallback
            result.append(vo)
        return result

    def batch_delete(
        self,
        db: Session,
        dto: BomWeldingFeeBatchDeleteDTO,
    ) -> BomWeldingFeeBatchDeleteResultVO:
        location, vehicle_model, bom_version = _normalize_scope(
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            bom_version=dto.bom_version,
        )
        source_node_ids = BomPeriodService().node_ids_for_l0_version(
            db,
            bom_version=bom_version,
            location=location,
            vehicle_model=vehicle_model,
        )
        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            statuses=[AUDIT_APPROVED],
            level=dto.level,
            levels=dto.levels,
        )
        deleted = self.fee_repo.delete_unaudited_by_scope(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            level=dto.level,
            levels=dto.levels,
        )
        db.commit()
        return BomWeldingFeeBatchDeleteResultVO(
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
        dto: BomWeldingFeeBatchApproveDTO,
        current_user: UserVO,
    ) -> BomWeldingFeeBatchAuditResultVO:
        location, vehicle_model, bom_version = _normalize_scope(
            location=dto.location,
            vehicle_model=dto.vehicle_model,
            bom_version=dto.bom_version,
        )
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")
        source_node_ids = BomPeriodService().node_ids_for_l0_version(
            db,
            bom_version=bom_version,
            location=location,
            vehicle_model=vehicle_model,
        )

        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            statuses=[AUDIT_APPROVED],
            level=dto.level,
            levels=dto.levels,
        )
        updated = self.fee_repo.approve_by_scope(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            audited_by=operator,
            audited_at=now(),
            audit_remark=(dto.audit_remark or "").strip() or None,
            updated_by=operator,
            level=dto.level,
            levels=dto.levels,
        )
        db.commit()
        return BomWeldingFeeBatchAuditResultVO(
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
        dto: BomWeldingFeeBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> BomWeldingFeeBatchAuditResultVO:
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
        source_node_ids = BomPeriodService().node_ids_for_l0_version(
            db,
            bom_version=bom_version,
            location=location,
            vehicle_model=vehicle_model,
        )

        skipped = self.fee_repo.count_by_scope_and_statuses(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            statuses=[AUDIT_PENDING, AUDIT_REJECTED],
            level=dto.level,
            levels=dto.levels,
        )
        updated = self.fee_repo.reverse_by_scope(
            db,
            year=dto.year,
            location=location,
            vehicle_model=vehicle_model,
            source_node_ids=source_node_ids,
            reverse_audited_by=operator,
            reverse_audited_at=now(),
            reverse_audit_remark=remark,
            updated_by=operator,
            level=dto.level,
            levels=dto.levels,
        )
        db.commit()
        return BomWeldingFeeBatchAuditResultVO(
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
        return LocationService().list_registered(db)

    def list_vehicle_models(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
    ) -> list[str]:
        return VehicleModelService().list_filter_codes(db, location)

    def list_bom_versions(
        self,
        db: Session,
        year: int | None = None,
        location: str | None = None,
        vehicle_model: str | None = None,
    ) -> list[str]:
        locations: list[str] | None = None
        if location:
            locations = LocationService().expand_for_query(db, location)
            if not locations:
                return []
        return BomPeriodService().list_l0_versions(
            db,
            locations=locations,
            vehicle_model=vehicle_model,
            year=year,
        )
