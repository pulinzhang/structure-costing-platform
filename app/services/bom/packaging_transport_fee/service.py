"""
BOM 包装运输费 Service
"""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, audit_create, display_name
from app.common.period import is_costing_year
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
    PackagingTransportFeeListFilters,
)
from app.schemas.common.batch_result import batch_approve_message, batch_reverse_message
from app.schemas.dto.bom_packaging_transport_fee_dto import (
    BomPackagingTransportFeeBatchApproveDTO,
    BomPackagingTransportFeeBatchReverseAuditDTO,
    BomPackagingTransportFeeCreate,
    BomPackagingTransportFeeQuery,
    BomPackagingTransportFeeUpdate,
)
from app.schemas.vo.bom_packaging_transport_fee_vo import (
    BomPackagingTransportFeeBatchAuditResultVO,
    BomPackagingTransportFeeBatchDeleteResultVO,
    BomPackagingTransportFeeResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.bom.packaging_transport_fee.engineering_change import (
    EngineeringChangePackagingFeeCloneResult,
    clone_revise_for_engineering_change as clone_revise_packaging_fee,
    delete_for_engineering_change_rollback as delete_packaging_fee_for_rollback,
)
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.vehicle_model.service import VehicleModelService

logger = logging.getLogger("service.bom")


class BomPackagingTransportFeeService:
    """包装运输费业务逻辑"""

    def __init__(self) -> None:
        self.repository = BomPackagingTransportFeeRepository()

    def paginate(
        self, db: Session, query: BomPackagingTransportFeeQuery
    ) -> tuple[
        list[BomPackagingTransportFeeResponse],
        int,
        PackagingTransportFeeListFilters,
    ]:
        skip = (query.page - 1) * query.size
        audit_status = query.audit_status.strip() if query.audit_status else None
        keyword = query.keyword.strip() if query.keyword else None
        vehicle_model = query.vehicle_model.strip() if query.vehicle_model else None
        location_service = LocationService()
        locations: list[str] | None = None
        if query.location:
            locations = location_service.expand_for_query(db, query.location)
            if not locations:
                empty_filters: PackagingTransportFeeListFilters = {
                    "locations": location_service.list_registered(db),
                    "years": self.repository.get_distinct_years(db),
                    "vehicle_models": VehicleModelService().list_filter_codes(db, query.location),
                    "audit_status": audit_status,
                    "summary": {
                        "total_count": 0,
                        "pending_count": 0,
                        "approved_count": 0,
                    },
                }
                return [], 0, empty_filters
        records, total = self.repository.paginate(
            db,
            locations=locations,
            year=query.year,
            vehicle_model=vehicle_model,
            audit_status=audit_status,
            keyword=keyword,
            skip=skip,
            limit=query.size,
        )
        rows = [BomPackagingTransportFeeResponse.model_validate(r) for r in records]
        filters: PackagingTransportFeeListFilters = {
            "locations": location_service.list_registered(db),
            "years": self.repository.get_distinct_years(db),
            "vehicle_models": VehicleModelService().list_filter_codes(db, query.location),
            "audit_status": audit_status,
            "summary": self.repository.summarize_by_filters(
                db,
                locations=locations,
                year=query.year,
                vehicle_model=vehicle_model,
                audit_status=audit_status,
                keyword=keyword,
            ),
        }
        return rows, total, filters

    def get_by_id(self, db: Session, id: int) -> BomPackagingTransportFeeResponse:
        record = self.repository.get_by_id(db, id)
        if not record:
            raise NotFoundException(f"包装运输费记录不存在: id={id}")
        return BomPackagingTransportFeeResponse.model_validate(record)

    def create(
        self,
        db: Session,
        data: BomPackagingTransportFeeCreate,
        current_user: UserVO,
    ) -> BomPackagingTransportFeeResponse:
        try:
            canonical = LocationService().require_enabled(db, data.location)
            if canonical != data.location:
                data = data.model_copy(update={"location": canonical})
            audit = audit_create(current_user)
            record = self.repository.create(
                db,
                data,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            )
            db.commit()
            db.refresh(record)
            return BomPackagingTransportFeeResponse.model_validate(record)
        except IntegrityError:
            db.rollback()
            raise BusinessException(
                f"该基地({data.location})、年份({data.year})、项目({data.vehicle_model})"
                f"和零件「{data.part_number}」的记录已存在"
            ) from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建包装运输费失败")
            raise

    def update(
        self,
        db: Session,
        id: int,
        data: BomPackagingTransportFeeUpdate,
        current_user: UserVO,
    ) -> BomPackagingTransportFeeResponse:
        existing = self.repository.get_by_id(db, id)
        if not existing:
            raise NotFoundException("记录不存在")
        if existing.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再修改")
        try:
            record = self.repository.update(
                db,
                id,
                data,
                updated_by=display_name(current_user),
            )
            if not record:
                raise NotFoundException("记录不存在")
            db.commit()
            db.refresh(record)
            return BomPackagingTransportFeeResponse.model_validate(record)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新包装运输费失败")
            raise

    def delete(self, db: Session, id: int) -> None:
        record = self.repository.get_by_id(db, id)
        if not record:
            raise NotFoundException("记录不存在")
        if record.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再删除")
        try:
            success = self.repository.delete(db, id)
            if not success:
                raise NotFoundException("记录不存在")
            db.commit()
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("删除包装运输费失败")
            raise

    def batch_delete_by_scope(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        vehicle_model: str,
    ) -> BomPackagingTransportFeeBatchDeleteResultVO:
        location = (location or "").strip()
        vehicle_model = (vehicle_model or "").strip()
        if not location:
            raise BusinessException("请选择采购基地")
        if not vehicle_model:
            raise BusinessException("请选择项目")
        if not is_costing_year(year):
            raise BusinessException("请选择正确的年度")

        existing = self.repository.list_by_scope(db, location, year, vehicle_model)
        if not existing:
            raise BusinessException(
                f"基地「{location}」{year} 年项目「{vehicle_model}」没有可删除的数据"
            )

        try:
            skipped = self.repository.count_by_scope_and_statuses(
                db,
                location=location,
                year=year,
                vehicle_model=vehicle_model,
                statuses=[AUDIT_APPROVED],
            )
            deleted_count = self.repository.delete_unaudited_by_scope(
                db, location, year, vehicle_model
            )
            db.commit()
            db.expire_all()
        except Exception:
            db.rollback()
            logger.exception("批量删除包装运输费失败")
            raise

        message = (
            f"已删除基地「{location}」{year} 年项目「{vehicle_model}」" f"共 {deleted_count} 条"
        )
        if skipped:
            message += f"，跳过已审核 {skipped} 条"
        return BomPackagingTransportFeeBatchDeleteResultVO(
            location=location,
            year=year,
            vehicle_model=vehicle_model,
            deleted_count=deleted_count,
            skipped_approved_count=skipped,
            message=message,
        )

    def batch_approve(
        self,
        db: Session,
        dto: BomPackagingTransportFeeBatchApproveDTO,
        current_user: UserVO,
    ) -> BomPackagingTransportFeeBatchAuditResultVO:
        location = (dto.location or "").strip()
        vehicle_model = (dto.vehicle_model or "").strip()
        if not location:
            raise BusinessException("请选择采购基地")
        if not vehicle_model:
            raise BusinessException("请选择项目")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        try:
            skipped = self.repository.count_by_scope_and_statuses(
                db,
                location=location,
                year=dto.year,
                vehicle_model=vehicle_model,
                statuses=[AUDIT_APPROVED],
            )
            updated = self.repository.approve_by_scope(
                db,
                location=location,
                year=dto.year,
                vehicle_model=vehicle_model,
                audited_by=operator,
                audited_at=now(),
                audit_remark=(dto.audit_remark or "").strip() or None,
                updated_by=operator,
            )
            db.commit()
            db.expire_all()
        except Exception:
            db.rollback()
            logger.exception("批量审核包装运输费失败")
            raise

        return BomPackagingTransportFeeBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=location,
            year=dto.year,
            vehicle_model=vehicle_model,
            message=batch_approve_message(updated, skipped),
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: BomPackagingTransportFeeBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> BomPackagingTransportFeeBatchAuditResultVO:
        location = (dto.location or "").strip()
        vehicle_model = (dto.vehicle_model or "").strip()
        if not location:
            raise BusinessException("请选择采购基地")
        if not vehicle_model:
            raise BusinessException("请选择项目")
        remark = (dto.reverse_audit_remark or "").strip()
        if not remark:
            raise BusinessException("反审核原因必填")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        try:
            skipped = self.repository.count_by_scope_and_statuses(
                db,
                location=location,
                year=dto.year,
                vehicle_model=vehicle_model,
                statuses=[AUDIT_PENDING],
            )
            updated = self.repository.reverse_by_scope(
                db,
                location=location,
                year=dto.year,
                vehicle_model=vehicle_model,
                reverse_audited_by=operator,
                reverse_audited_at=now(),
                reverse_audit_remark=remark,
                updated_by=operator,
            )
            db.commit()
            db.expire_all()
        except Exception:
            db.rollback()
            logger.exception("批量反审核包装运输费失败")
            raise

        return BomPackagingTransportFeeBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=location,
            year=dto.year,
            vehicle_model=vehicle_model,
            message=batch_reverse_message(updated, skipped),
        )

    def get_locations(self, db: Session) -> list[str]:
        return LocationService().list_registered(db)

    def get_years(self, db: Session) -> list[int]:
        return self.repository.get_distinct_years(db)

    def get_vehicle_models(self, db: Session) -> list[str]:
        return VehicleModelService().list_filter_codes(db)

    def clone_revise_for_engineering_change(
        self,
        db: Session,
        *,
        location: str,
        vehicle_model: str,
        old_part_number: str,
        new_part_number: str,
        from_year: int,
        current_user: UserVO,
    ) -> list[EngineeringChangePackagingFeeCloneResult]:
        """种新树抄包装运输费。只 flush。实现见 engineering_change。"""
        return clone_revise_packaging_fee(
            self.repository,
            db,
            location=location,
            vehicle_model=vehicle_model,
            old_part_number=old_part_number,
            new_part_number=new_part_number,
            from_year=from_year,
            current_user=current_user,
        )

    def delete_for_engineering_change_rollback(self, db: Session, fee_id: int) -> None:
        """回滚删新包装运输费行。只 flush。"""
        delete_packaging_fee_for_rollback(self.repository, db, fee_id)
