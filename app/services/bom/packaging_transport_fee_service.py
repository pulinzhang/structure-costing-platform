"""
BOM 包装运输费 Service
"""

import logging
from typing import List, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, audit_create, display_name
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.bom.packaging_transport_fee_repository import (
    BomPackagingTransportFeeRepository,
    PackagingTransportFeeListFilters,
)
from app.schemas.dto.bom_packaging_transport_fee_dto import (
    BomPackagingTransportFeeBatchApproveDTO,
    BomPackagingTransportFeeBatchReverseAuditDTO,
    BomPackagingTransportFeeCreate,
    BomPackagingTransportFeeQuery,
    BomPackagingTransportFeeUpdate,
)
from app.schemas.vo.bom_packaging_transport_fee_vo import (
    BomPackagingTransportFeeBatchAuditResultVO,
    BomPackagingTransportFeeResponse,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.bom")


class BomPackagingTransportFeeService:
    """包装运输费业务逻辑"""

    def __init__(self) -> None:
        self.repository = BomPackagingTransportFeeRepository()

    def paginate(
        self, db: Session, query: BomPackagingTransportFeeQuery
    ) -> Tuple[
        List[BomPackagingTransportFeeResponse],
        int,
        PackagingTransportFeeListFilters,
    ]:
        skip = (query.page - 1) * query.size
        audit_status = query.audit_status.strip() if query.audit_status else None
        keyword = query.keyword.strip() if query.keyword else None
        vehicle_model = query.vehicle_model.strip() if query.vehicle_model else None
        records, total = self.repository.paginate(
            db,
            location=query.location,
            year=query.year,
            vehicle_model=vehicle_model,
            audit_status=audit_status,
            keyword=keyword,
            skip=skip,
            limit=query.size,
        )
        rows = [BomPackagingTransportFeeResponse.model_validate(r) for r in records]
        filters: PackagingTransportFeeListFilters = {
            "locations": self.repository.get_distinct_locations(db),
            "years": self.repository.get_distinct_years(db),
            "vehicle_models": self.repository.get_distinct_vehicle_models(db),
            "audit_status": audit_status,
            "summary": self.repository.summarize_by_filters(
                db,
                location=query.location,
                year=query.year,
                vehicle_model=vehicle_model,
                audit_status=audit_status,
                keyword=keyword,
            ),
        }
        return rows, total, filters

    def get_by_id(
        self, db: Session, id: int
    ) -> BomPackagingTransportFeeResponse:
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
    ) -> Tuple[int, int]:
        location = (location or "").strip()
        vehicle_model = (vehicle_model or "").strip()
        if not location:
            raise BusinessException("请选择采购基地")
        if not vehicle_model:
            raise BusinessException("请选择项目")
        if year < 2000 or year > 2100:
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

        return deleted_count, skipped

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
        )

    def get_locations(self, db: Session) -> List[str]:
        return self.repository.get_distinct_locations(db)

    def get_years(self, db: Session) -> List[int]:
        return self.repository.get_distinct_years(db)

    def get_vehicle_models(self, db: Session) -> List[str]:
        return self.repository.get_distinct_vehicle_models(db)
