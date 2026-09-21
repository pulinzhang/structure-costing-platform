"""
BOM 年度零件价 Service
业务逻辑层，处理业务规则和事务
"""

import logging
from typing import TypedDict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import (
    AUDIT_APPROVED,
    AUDIT_PENDING,
    audit_create,
    display_name,
)
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.models.bom.annual_part_price import BomAnnualPartPrice
from app.parsers.bom.annual_part_price_parser import (
    DEFAULT_CONVERSION_FACTOR,
    resolve_annual_unit_price,
)
from app.repositories.bom.annual_part_price_repository import (
    AuditCountSummary,
    BomAnnualPartPriceRepository,
)
from app.schemas.common.batch_result import batch_approve_message, batch_reverse_message
from app.schemas.dto.bom_annual_part_price_dto import (
    BomAnnualPartPriceBatchApproveDTO,
    BomAnnualPartPriceBatchReverseAuditDTO,
    BomAnnualPartPriceCreate,
    BomAnnualPartPriceQuery,
    BomAnnualPartPriceUpdate,
)
from app.schemas.vo.bom_annual_part_price_vo import (
    BomAnnualPartPriceBatchAuditResultVO,
    BomAnnualPartPriceBatchDeleteResultVO,
    BomAnnualPartPriceResponse,
)
from app.schemas.vo.supplier_vo import SupplierChoiceVO
from app.schemas.vo.user_vo import UserVO
from app.services.bom.annual_part_price.engineering_change import (
    EngineeringChangeAnnualPartPriceCloneResult,
)
from app.services.bom.annual_part_price.engineering_change import (
    clone_revise_for_engineering_change as clone_revise_annual_part_price,
)
from app.services.bom.annual_part_price.engineering_change import (
    delete_for_engineering_change_rollback as delete_annual_part_price_for_rollback,
)
from app.services.masterdata.location.service import LocationService
from app.services.masterdata.supplier.service import SupplierService

logger = logging.getLogger("service.bom")


def _apply_create_conversion(data: BomAnnualPartPriceCreate) -> BomAnnualPartPriceCreate:
    try:
        unit_price = resolve_annual_unit_price(
            purchase_unit_price=data.purchase_unit_price,
            conversion_factor=data.conversion_factor,
            unit_price=data.unit_price,
        )
    except ValueError as exc:
        raise BusinessException(str(exc)) from None
    return data.model_copy(update={"unit_price": unit_price})


def _apply_update_conversion(
    existing: BomAnnualPartPrice,
    data: BomAnnualPartPriceUpdate,
) -> BomAnnualPartPriceUpdate:
    fields = data.model_fields_set
    purchase_unit_price = (
        data.purchase_unit_price
        if "purchase_unit_price" in fields
        else existing.purchase_unit_price
    )
    if "conversion_factor" in fields and data.conversion_factor is not None:
        conversion_factor = data.conversion_factor
    else:
        conversion_factor = existing.conversion_factor or DEFAULT_CONVERSION_FACTOR
    try:
        unit_price = resolve_annual_unit_price(
            purchase_unit_price=purchase_unit_price,
            conversion_factor=conversion_factor,
            unit_price=data.unit_price,
        )
    except ValueError as exc:
        raise BusinessException(str(exc)) from None
    return data.model_copy(
        update={
            "unit_price": unit_price,
            "conversion_factor": conversion_factor,
        }
    )


class AnnualPartPriceListFilters(TypedDict):
    """列表筛选项（Service 组装；含上游供应商下拉）。"""

    locations: list[str]
    years: list[int]
    audit_status: str | None
    summary: AuditCountSummary
    suppliers: list[SupplierChoiceVO]


class BomAnnualPartPriceService:
    """年度零件价业务逻辑"""

    def __init__(self) -> None:
        self.repository = BomAnnualPartPriceRepository()

    def list_by_year(self, db: Session, year: int) -> list[BomAnnualPartPriceResponse]:
        records = self.repository.list_by_year(db, year)
        return [BomAnnualPartPriceResponse.model_validate(r) for r in records]

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> list[BomAnnualPartPriceResponse]:
        records = self.repository.list_by_location_year(db, location, year)
        return [BomAnnualPartPriceResponse.model_validate(r) for r in records]

    def list_all(self, db: Session) -> list[BomAnnualPartPriceResponse]:
        records = self.repository.list_all(db)
        return [BomAnnualPartPriceResponse.model_validate(r) for r in records]

    def paginate(
        self, db: Session, query: BomAnnualPartPriceQuery
    ) -> tuple[list[BomAnnualPartPriceResponse], int, AnnualPartPriceListFilters]:
        skip = (query.page - 1) * query.size
        audit_status = query.audit_status.strip() if query.audit_status else None
        keyword = query.keyword.strip() if query.keyword else None
        location_service = LocationService()
        supplier_choices = SupplierService().list_enabled_choices(db)
        locations: list[str] | None = None
        if query.location:
            locations = location_service.expand_for_query(db, query.location)
            if not locations:
                empty_filters: AnnualPartPriceListFilters = {
                    "locations": location_service.list_registered(db),
                    "years": self.repository.get_distinct_years(db),
                    "audit_status": audit_status,
                    "summary": {
                        "total_count": 0,
                        "pending_count": 0,
                        "approved_count": 0,
                    },
                    "suppliers": supplier_choices,
                }
                return [], 0, empty_filters
        records, total = self.repository.paginate(
            db,
            locations=locations,
            year=query.year,
            audit_status=audit_status,
            keyword=keyword,
            skip=skip,
            limit=query.size,
        )
        rows = [BomAnnualPartPriceResponse.model_validate(r) for r in records]
        filters: AnnualPartPriceListFilters = {
            "locations": location_service.list_registered(db),
            "years": self.repository.get_distinct_years(db),
            "audit_status": audit_status,
            "summary": self.repository.summarize_by_filters(
                db,
                locations=locations,
                year=query.year,
                audit_status=audit_status,
                keyword=keyword,
            ),
            "suppliers": supplier_choices,
        }
        return rows, total, filters

    def get_by_id(self, db: Session, id: int) -> BomAnnualPartPriceResponse:
        record = self.repository.get_by_id(db, id)
        if not record:
            raise NotFoundException(f"年度零件价记录不存在: id={id}")
        return BomAnnualPartPriceResponse.model_validate(record)

    def create(
        self,
        db: Session,
        data: BomAnnualPartPriceCreate,
        current_user: UserVO,
    ) -> BomAnnualPartPriceResponse:
        try:
            canonical = LocationService().require_enabled(db, data.location)
            if canonical != data.location:
                data = data.model_copy(update={"location": canonical})
            data = _apply_create_conversion(data)
            audit = audit_create(current_user)
            record = self.repository.create(
                db,
                data,
                created_by=audit["created_by"],
                updated_by=audit["updated_by"],
            )
            db.commit()
            db.refresh(record)
            return BomAnnualPartPriceResponse.model_validate(record)
        except IntegrityError:
            db.rollback()
            raise BusinessException(
                f"该基地({data.location})、年份({data.year})"
                f"和零件「{data.part_number}」的记录已存在"
            ) from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建年度零件价失败")
            raise

    def update(
        self,
        db: Session,
        id: int,
        data: BomAnnualPartPriceUpdate,
        current_user: UserVO,
    ) -> BomAnnualPartPriceResponse:
        existing = self.repository.get_by_id(db, id)
        if not existing:
            raise NotFoundException("记录不存在")
        if existing.audit_status == AUDIT_APPROVED:
            raise BusinessException("已审核通过，请先反审核后再修改")
        data = _apply_update_conversion(existing, data)
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
            return BomAnnualPartPriceResponse.model_validate(record)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新年度零件价失败")
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
            logger.exception("删除年度零件价失败")
            raise

    def batch_delete_by_location_year(
        self,
        db: Session,
        *,
        location: str,
        year: int,
    ) -> BomAnnualPartPriceBatchDeleteResultVO:
        location = (location or "").strip()
        if not location:
            raise BusinessException("请选择采购基地")
        if year < 2000 or year > 2100:
            raise BusinessException("请选择正确的年度")

        existing = self.repository.list_by_location_year(db, location, year)
        if not existing:
            raise BusinessException(f"基地「{location}」{year} 年没有可删除的数据")

        try:
            skipped = self.repository.count_by_location_year_and_statuses(
                db,
                location=location,
                year=year,
                statuses=[AUDIT_APPROVED],
            )
            deleted_count = self.repository.delete_unaudited_by_location_year(db, location, year)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("批量删除年度零件价失败")
            raise

        logger.info(
            "批量删除年度零件价: location=%s year=%s deleted=%s skipped=%s",
            location,
            year,
            deleted_count,
            skipped,
        )
        message = f"已删除基地「{location}」{year} 年共 {deleted_count} 条"
        if skipped:
            message += f"，跳过已审核 {skipped} 条"
        return BomAnnualPartPriceBatchDeleteResultVO(
            location=location,
            year=year,
            deleted_count=deleted_count,
            skipped_approved_count=skipped,
            message=message,
        )

    def batch_approve(
        self,
        db: Session,
        dto: BomAnnualPartPriceBatchApproveDTO,
        current_user: UserVO,
    ) -> BomAnnualPartPriceBatchAuditResultVO:
        location = (dto.location or "").strip()
        if not location:
            raise BusinessException("请选择采购基地")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        try:
            skipped = self.repository.count_by_location_year_and_statuses(
                db,
                location=location,
                year=dto.year,
                statuses=[AUDIT_APPROVED],
            )
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
            logger.exception("批量审核年度零件价失败")
            raise

        return BomAnnualPartPriceBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=location,
            year=dto.year,
            message=batch_approve_message(updated, skipped),
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: BomAnnualPartPriceBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> BomAnnualPartPriceBatchAuditResultVO:
        location = (dto.location or "").strip()
        if not location:
            raise BusinessException("请选择采购基地")
        remark = (dto.reverse_audit_remark or "").strip()
        if not remark:
            raise BusinessException("反审核原因必填")
        operator = display_name(current_user)
        if not operator:
            raise BusinessException("无法识别当前登录用户")

        try:
            skipped = self.repository.count_by_location_year_and_statuses(
                db,
                location=location,
                year=dto.year,
                statuses=[AUDIT_PENDING],
            )
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
            logger.exception("批量反审核年度零件价失败")
            raise

        return BomAnnualPartPriceBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=location,
            year=dto.year,
            message=batch_reverse_message(updated, skipped),
        )

    def get_locations(self, db: Session) -> list[str]:
        return LocationService().list_registered(db)

    def get_years(self, db: Session) -> list[int]:
        return self.repository.get_distinct_years(db)

    def clone_revise_for_engineering_change(
        self,
        db: Session,
        *,
        location: str,
        old_part_number: str,
        new_part_number: str,
        from_year: int,
        current_user: UserVO,
    ) -> list[EngineeringChangeAnnualPartPriceCloneResult]:
        """换号抄年度零件价。只 flush。实现见 engineering_change。"""
        return clone_revise_annual_part_price(
            self.repository,
            db,
            location=location,
            old_part_number=old_part_number,
            new_part_number=new_part_number,
            from_year=from_year,
            current_user=current_user,
        )

    def delete_for_engineering_change_rollback(self, db: Session, price_id: int) -> None:
        """回滚删新年度零件价行。只 flush。"""
        delete_annual_part_price_for_rollback(self.repository, db, price_id)
