"""
焊接工费单价 Service
业务逻辑层，处理业务规则和事务
"""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import (
    AUDIT_APPROVED,
    AUDIT_PENDING,
    audit_create,
    display_name,
)
from app.common.bom.welding_standard_process import validate_welding_unit_price_catalog
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.bom.welding_unit_price_repository import (
    BomWeldingUnitPriceRepository,
    WeldingUnitPriceListFilters,
)
from app.schemas.dto.bom_welding_unit_price_dto import (
    BomWeldingUnitPriceBatchApproveDTO,
    BomWeldingUnitPriceBatchReverseAuditDTO,
    BomWeldingUnitPriceCreate,
    BomWeldingUnitPriceQuery,
    BomWeldingUnitPriceUpdate,
)
from app.schemas.vo.bom_welding_unit_price_vo import (
    BomWeldingUnitPriceBatchAuditResultVO,
    BomWeldingUnitPriceResponse,
)
from app.schemas.vo.user_vo import UserVO
from app.services.masterdata.location.service import LocationService

logger = logging.getLogger("service.bom")


class BomWeldingUnitPriceService:
    """焊接工费单价业务逻辑"""

    def __init__(self) -> None:
        self.repository = BomWeldingUnitPriceRepository()

    def list_by_year(self, db: Session, year: int) -> list[BomWeldingUnitPriceResponse]:
        records = self.repository.list_by_year(db, year)
        return [BomWeldingUnitPriceResponse.model_validate(r) for r in records]

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> list[BomWeldingUnitPriceResponse]:
        records = self.repository.list_by_location_year(db, location, year)
        return [BomWeldingUnitPriceResponse.model_validate(r) for r in records]

    def list_all(self, db: Session) -> list[BomWeldingUnitPriceResponse]:
        records = self.repository.list_all(db)
        return [BomWeldingUnitPriceResponse.model_validate(r) for r in records]

    def paginate(
        self, db: Session, query: BomWeldingUnitPriceQuery
    ) -> tuple[list[BomWeldingUnitPriceResponse], int, WeldingUnitPriceListFilters]:
        skip = (query.page - 1) * query.size
        audit_status = query.audit_status.strip() if query.audit_status else None
        location_service = LocationService()
        locations: list[str] | None = None
        if query.location:
            locations = location_service.expand_for_query(db, query.location)
            if not locations:
                empty_filters: WeldingUnitPriceListFilters = {
                    "locations": location_service.list_registered(db),
                    "years": self.repository.get_distinct_years(db),
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
            audit_status=audit_status,
            skip=skip,
            limit=query.size,
        )
        rows = [BomWeldingUnitPriceResponse.model_validate(r) for r in records]
        filters: WeldingUnitPriceListFilters = {
            "locations": location_service.list_registered(db),
            "years": self.repository.get_distinct_years(db),
            "audit_status": audit_status,
            "summary": self.repository.summarize_by_filters(
                db,
                locations=locations,
                year=query.year,
                audit_status=audit_status,
            ),
        }
        return rows, total, filters

    def get_by_id(self, db: Session, id: int) -> BomWeldingUnitPriceResponse:
        record = self.repository.get_by_id(db, id)
        if not record:
            raise NotFoundException(f"焊接单价记录不存在: id={id}")
        return BomWeldingUnitPriceResponse.model_validate(record)

    def create(
        self,
        db: Session,
        data: BomWeldingUnitPriceCreate,
        current_user: UserVO,
    ) -> BomWeldingUnitPriceResponse:
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
            return BomWeldingUnitPriceResponse.model_validate(record)
        except IntegrityError:
            db.rollback()
            raise BusinessException(
                f"该基地({data.location})、年份({data.year})"
                f"和项目「{data.item_name}」的记录已存在"
            ) from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建焊接工费单价失败")
            raise

    def bulk_upsert(
        self,
        db: Session,
        items: list[BomWeldingUnitPriceCreate],
        current_user: UserVO,
    ) -> tuple[
        list[BomWeldingUnitPriceResponse],
        list[BomWeldingUnitPriceResponse],
        list[str],
        int,
    ]:
        created: list[BomWeldingUnitPriceResponse] = []
        updated: list[BomWeldingUnitPriceResponse] = []
        failed: list[str] = []
        skipped_approved = 0

        for item in items:
            existing = self.repository.get_by_location_year_item(
                db, item.location, item.year, item.item_name
            )
            if existing:
                if existing.audit_status == AUDIT_APPROVED:
                    skipped_approved += 1
                    continue
                try:
                    record = self.update(
                        db,
                        existing.id,
                        BomWeldingUnitPriceUpdate(
                            unit=item.unit,
                            unit_price=item.unit_price,
                            remark=item.remark,
                        ),
                        current_user=current_user,
                    )
                    updated.append(record)
                except BusinessException as error:
                    failed.append(
                        str(error) or f"{item.location}/{item.year}/{item.item_name} 更新失败"
                    )
                continue

            try:
                record = self.create(db, item, current_user=current_user)
                created.append(record)
            except BusinessException as error:
                failed.append(str(error) or "未知错误")

        return created, updated, failed, skipped_approved

    def update(
        self,
        db: Session,
        id: int,
        data: BomWeldingUnitPriceUpdate,
        current_user: UserVO,
    ) -> BomWeldingUnitPriceResponse:
        existing = self.repository.get_by_id(db, id)
        if not existing:
            raise NotFoundException("记录不存在")
        if existing.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再修改")

        unit_to_check = data.unit if data.unit is not None else existing.unit
        try:
            validate_welding_unit_price_catalog(existing.item_name, unit_to_check)
        except ValueError as exc:
            raise BusinessException(str(exc)) from exc

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
            return BomWeldingUnitPriceResponse.model_validate(record)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新焊接工费单价失败")
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
            logger.exception("删除焊接工费单价失败")
            raise

    def batch_delete_by_location_year(
        self,
        db: Session,
        *,
        location: str,
        year: int,
    ) -> tuple[int, int]:
        location = (location or "").strip()
        if not location:
            raise BusinessException("请选择采购基地")
        if year < 2000 or year > 2100:
            raise BusinessException("请选择正确的年度")

        existing = self.repository.list_by_location_year(db, location, year)
        if not existing:
            raise BusinessException(f"基地「{location}」{year} 年没有可删除的数据")

        skipped = self.repository.count_by_location_year_and_statuses(
            db,
            location=location,
            year=year,
            statuses=[AUDIT_APPROVED],
        )
        try:
            deleted_count = self.repository.delete_unaudited_by_location_year(db, location, year)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("批量删除焊接工费单价失败")
            raise
        logger.info(
            "批量删除焊接工费单价: location=%s year=%s deleted=%s skipped=%s",
            location,
            year,
            deleted_count,
            skipped,
        )
        return deleted_count, skipped

    def batch_approve(
        self,
        db: Session,
        dto: BomWeldingUnitPriceBatchApproveDTO,
        current_user: UserVO,
    ) -> BomWeldingUnitPriceBatchAuditResultVO:
        location = (dto.location or "").strip()
        if not location:
            raise BusinessException("请选择采购基地")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        skipped = self.repository.count_by_location_year_and_statuses(
            db,
            location=location,
            year=dto.year,
            statuses=[AUDIT_APPROVED],
        )
        try:
            updated = self.repository.approve_by_location_year(
                db,
                location=location,
                year=dto.year,
                audited_by=operator,
                audited_at=now(),
                audit_remark=(dto.audit_remark or "").strip() or None,
                updated_by=operator,
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("批量审核焊接工费单价失败")
            raise
        return BomWeldingUnitPriceBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=location,
            year=dto.year,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: BomWeldingUnitPriceBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> BomWeldingUnitPriceBatchAuditResultVO:
        location = (dto.location or "").strip()
        if not location:
            raise BusinessException("请选择采购基地")
        remark = (dto.reverse_audit_remark or "").strip()
        if not remark:
            raise BusinessException("反审核原因必填")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        skipped = self.repository.count_by_location_year_and_statuses(
            db,
            location=location,
            year=dto.year,
            statuses=[AUDIT_PENDING],
        )
        try:
            updated = self.repository.reverse_by_location_year(
                db,
                location=location,
                year=dto.year,
                reverse_audited_by=operator,
                reverse_audited_at=now(),
                reverse_audit_remark=remark,
                updated_by=operator,
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("批量反审核焊接工费单价失败")
            raise
        return BomWeldingUnitPriceBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=location,
            year=dto.year,
        )

    def get_locations(self, db: Session) -> list[str]:
        return LocationService().list_enabled(db)

    def get_years(self, db: Session) -> list[int]:
        return self.repository.get_distinct_years(db)
