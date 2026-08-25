"""
冲次单价 Service
业务逻辑层，处理业务规则和事务
"""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.audit import (
    AUDIT_APPROVED,
    AUDIT_PENDING,
    audit_create,
    audit_update,
    display_name,
)
from app.common.timezone import now
from app.exceptions.base import BusinessException, NotFoundException
from app.repositories.stamping.tonnage_price_repository import (
    StampingTonnagePriceRepository,
    TonnagePriceListFilters,
)
from app.schemas.dto.stamping_tonnage_price_dto import (
    StampingTonnagePriceBatchApproveDTO,
    StampingTonnagePriceBatchReverseAuditDTO,
    StampingTonnagePriceCreate,
    StampingTonnagePriceQuery,
    StampingTonnagePriceUpdate,
)
from app.schemas.vo.stamping_tonnage_price_vo import (
    StampingTonnagePriceBatchAuditResultVO,
    StampingTonnagePriceResponse,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.stamping")


class StampingTonnagePriceService:
    """冲次单价业务逻辑"""

    def __init__(self) -> None:
        self.repository = StampingTonnagePriceRepository()

    def list_by_year(self, db: Session, year: int) -> list[StampingTonnagePriceResponse]:
        records = self.repository.list_by_year(db, year)
        return [StampingTonnagePriceResponse.model_validate(r) for r in records]

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> list[StampingTonnagePriceResponse]:
        records = self.repository.list_by_location_year(db, location, year)
        return [StampingTonnagePriceResponse.model_validate(r) for r in records]

    def list_all(self, db: Session) -> list[StampingTonnagePriceResponse]:
        records = self.repository.list_all(db)
        return [StampingTonnagePriceResponse.model_validate(r) for r in records]

    def paginate(
        self, db: Session, query: StampingTonnagePriceQuery
    ) -> tuple[list[StampingTonnagePriceResponse], int, TonnagePriceListFilters]:
        skip = (query.page - 1) * query.size
        audit_status = query.audit_status.strip() if query.audit_status else None
        records, total = self.repository.paginate(
            db,
            location=query.location,
            year=query.year,
            audit_status=audit_status,
            skip=skip,
            limit=query.size,
        )
        rows = [StampingTonnagePriceResponse.model_validate(r) for r in records]
        filters: TonnagePriceListFilters = {
            "locations": self.repository.get_distinct_locations(db),
            "years": self.repository.get_distinct_years(db),
            "tonnages": self.repository.get_distinct_tonnages(db),
            "audit_status": audit_status,
            "summary": self.repository.summarize_by_filters(
                db,
                location=query.location,
                year=query.year,
                audit_status=audit_status,
            ),
        }
        return rows, total, filters

    def get_by_id(self, db: Session, id: int) -> StampingTonnagePriceResponse:
        record = self.repository.get_by_id(db, id)
        if not record:
            raise NotFoundException(f"冲次单价记录不存在: id={id}")
        return StampingTonnagePriceResponse.model_validate(record)

    def create(
        self,
        db: Session,
        data: StampingTonnagePriceCreate,
        current_user: UserVO,
    ) -> StampingTonnagePriceResponse:
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
            return StampingTonnagePriceResponse.model_validate(record)
        except IntegrityError:
            db.rollback()
            raise BusinessException(
                f"该基地({data.location})、年份({data.year})和吨位({data.tonnage})的记录已存在"
            ) from None
        except BusinessException:
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("创建冲次单价失败")
            raise

    def bulk_upsert(
        self,
        db: Session,
        items: list[StampingTonnagePriceCreate],
        current_user: UserVO,
    ) -> tuple[
        list[StampingTonnagePriceResponse],
        list[StampingTonnagePriceResponse],
        list[str],
        int,
    ]:
        """
        批量写入冲次单价（与 Excel 导入一致：存在则更新单价）。
        已审核通过的记录跳过，不覆盖。
        返回 (新增列表, 更新列表, 失败错误信息列表, 跳过已审核条数)。
        """
        created: list[StampingTonnagePriceResponse] = []
        updated: list[StampingTonnagePriceResponse] = []
        failed: list[str] = []
        skipped_approved = 0

        for item in items:
            existing = self.repository.get_by_location_year_tonnage(
                db, item.location, item.year, item.tonnage
            )
            if existing:
                if existing.audit_status == AUDIT_APPROVED:
                    skipped_approved += 1
                    continue
                try:
                    record = self.update(
                        db,
                        existing.id,
                        StampingTonnagePriceUpdate(price_per_stroke=item.price_per_stroke),
                        current_user=current_user,
                    )
                    updated.append(record)
                except BusinessException as error:
                    failed.append(
                        str(error) or f"{item.location}/{item.year}/{item.tonnage}T 更新失败"
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
        data: StampingTonnagePriceUpdate,
        current_user: UserVO,
    ) -> StampingTonnagePriceResponse:
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
                updated_by=audit_update(current_user)["updated_by"],
            )
            if not record:
                raise NotFoundException("记录不存在")
            db.commit()
            db.refresh(record)
            return StampingTonnagePriceResponse.model_validate(record)
        except (BusinessException, NotFoundException):
            db.rollback()
            raise
        except Exception:
            db.rollback()
            logger.exception("更新冲次单价失败")
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
            logger.exception("删除冲次单价失败")
            raise

    def batch_delete_by_location_year(
        self,
        db: Session,
        *,
        location: str,
        year: int,
    ) -> tuple[int, int]:
        """按基地 + 年度批量删除未审核记录。返回 (删除条数, 跳过已审核条数)。"""
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
            logger.exception("批量删除冲次单价失败")
            raise
        logger.info(
            "批量删除冲次单价: location=%s year=%s deleted=%s skipped=%s",
            location,
            year,
            deleted_count,
            skipped,
        )
        return deleted_count, skipped

    def batch_approve(
        self,
        db: Session,
        dto: StampingTonnagePriceBatchApproveDTO,
        current_user: UserVO,
    ) -> StampingTonnagePriceBatchAuditResultVO:
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
            logger.exception("批量审核冲次单价失败")
            raise
        return StampingTonnagePriceBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=location,
            year=dto.year,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: StampingTonnagePriceBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> StampingTonnagePriceBatchAuditResultVO:
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
            logger.exception("批量反审核冲次单价失败")
            raise
        return StampingTonnagePriceBatchAuditResultVO(
            updated_count=updated,
            skipped_count=skipped,
            location=location,
            year=dto.year,
        )

    def get_locations(self, db: Session) -> list[str]:
        return self.repository.get_distinct_locations(db)

    def get_years(self, db: Session) -> list[int]:
        return self.repository.get_distinct_years(db)

    def get_tonnages(self, db: Session) -> list[int]:
        return self.repository.get_distinct_tonnages(db)
