"""
冲次单价 Service
业务逻辑层，处理业务规则和事务
"""

import logging
from typing import List, Optional, Tuple

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

    def list_by_year(
        self, db: Session, year: int
    ) -> List[StampingTonnagePriceResponse]:
        records = self.repository.list_by_year(db, year)
        return [StampingTonnagePriceResponse.model_validate(r) for r in records]

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> List[StampingTonnagePriceResponse]:
        records = self.repository.list_by_location_year(db, location, year)
        return [StampingTonnagePriceResponse.model_validate(r) for r in records]

    def list_all(self, db: Session) -> List[StampingTonnagePriceResponse]:
        records = self.repository.list_all(db)
        return [StampingTonnagePriceResponse.model_validate(r) for r in records]

    def paginate(
        self, db: Session, query: StampingTonnagePriceQuery
    ) -> Tuple[List[StampingTonnagePriceResponse], int, TonnagePriceListFilters]:
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

    def get_by_id(self, db: Session, id: int) -> Optional[StampingTonnagePriceResponse]:
        record = self.repository.get_by_id(db, id)
        if not record:
            return None
        return StampingTonnagePriceResponse.model_validate(record)

    def create(
        self,
        db: Session,
        data: StampingTonnagePriceCreate,
        current_user: UserVO,
    ) -> Tuple[Optional[StampingTonnagePriceResponse], Optional[str]]:
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
            return StampingTonnagePriceResponse.model_validate(record), None
        except IntegrityError:
            db.rollback()
            error_msg = (
                f"该基地({data.location})、年份({data.year})和吨位({data.tonnage})的记录已存在"
            )
            logger.warning(error_msg)
            return None, error_msg
        except Exception as e:
            db.rollback()
            logger.error(f"创建冲次单价失败: {e}")
            return None, str(e)

    def bulk_upsert(
        self,
        db: Session,
        items: List[StampingTonnagePriceCreate],
        current_user: UserVO,
    ) -> Tuple[
        List[StampingTonnagePriceResponse],
        List[StampingTonnagePriceResponse],
        List[str],
        int,
    ]:
        """
        批量写入冲次单价（与 Excel 导入一致：存在则更新单价）。
        已审核通过的记录跳过，不覆盖。
        返回 (新增列表, 更新列表, 失败错误信息列表, 跳过已审核条数)。
        """
        created: List[StampingTonnagePriceResponse] = []
        updated: List[StampingTonnagePriceResponse] = []
        failed: List[str] = []
        skipped_approved = 0

        for item in items:
            existing = self.repository.get_by_location_year_tonnage(
                db, item.location, item.year, item.tonnage
            )
            if existing:
                if existing.audit_status == AUDIT_APPROVED:
                    skipped_approved += 1
                    continue
                record, error = self.update(
                    db,
                    existing.id,
                    StampingTonnagePriceUpdate(price_per_stroke=item.price_per_stroke),
                    current_user=current_user,
                )
                if record:
                    updated.append(record)
                else:
                    failed.append(
                        error
                        or f"{item.location}/{item.year}/{item.tonnage}T 更新失败"
                    )
                continue

            record, error = self.create(db, item, current_user=current_user)
            if record:
                created.append(record)
            else:
                failed.append(error or "未知错误")

        return created, updated, failed, skipped_approved

    def update(
        self,
        db: Session,
        id: int,
        data: StampingTonnagePriceUpdate,
        current_user: UserVO,
    ) -> Tuple[Optional[StampingTonnagePriceResponse], Optional[str]]:
        try:
            existing = self.repository.get_by_id(db, id)
            if not existing:
                return None, "记录不存在"
            if existing.audit_status == AUDIT_APPROVED:
                return None, "已审核通过，请先反审核后再修改"

            record = self.repository.update(
                db,
                id,
                data,
                updated_by=audit_update(current_user)["updated_by"],
            )
            if not record:
                return None, "记录不存在"
            db.commit()
            db.refresh(record)
            return StampingTonnagePriceResponse.model_validate(record), None
        except Exception as e:
            db.rollback()
            logger.error(f"更新冲次单价失败: {e}")
            return None, str(e)

    def delete(self, db: Session, id: int) -> Tuple[bool, Optional[str]]:
        record = self.repository.get_by_id(db, id)
        if not record:
            return False, "记录不存在"
        if record.audit_status == AUDIT_APPROVED:
            return False, "已审核通过，请先反审核后再删除"
        try:
            success = self.repository.delete(db, id)
            if not success:
                return False, "记录不存在"
            db.commit()
            return True, None
        except Exception as e:
            db.rollback()
            logger.error("删除冲次单价失败: %s", e)
            return False, str(e)

    def batch_delete_by_location_year(
        self,
        db: Session,
        *,
        location: str,
        year: int,
    ) -> Tuple[int, int, Optional[str]]:
        """按基地 + 年度批量删除未审核记录。返回 (删除条数, 跳过已审核条数, 错误信息)。"""
        location = (location or "").strip()
        if not location:
            return 0, 0, "请选择采购基地"
        if year < 2000 or year > 2100:
            return 0, 0, "请选择正确的年度"

        existing = self.repository.list_by_location_year(db, location, year)
        if not existing:
            return 0, 0, f"基地「{location}」{year} 年没有可删除的数据"

        skipped = self.repository.count_by_location_year_and_statuses(
            db,
            location=location,
            year=year,
            statuses=[AUDIT_APPROVED],
        )
        try:
            deleted_count = self.repository.delete_unaudited_by_location_year(
                db, location, year
            )
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("批量删除冲次单价失败: %s", e)
            return 0, 0, str(e)
        logger.info(
            "批量删除冲次单价: location=%s year=%s deleted=%s skipped=%s",
            location,
            year,
            deleted_count,
            skipped,
        )
        return deleted_count, skipped, None

    def batch_approve(
        self,
        db: Session,
        dto: StampingTonnagePriceBatchApproveDTO,
        current_user: UserVO,
    ) -> Tuple[Optional[StampingTonnagePriceBatchAuditResultVO], Optional[str]]:
        location = (dto.location or "").strip()
        if not location:
            return None, "请选择采购基地"
        operator = display_name(current_user)
        if not operator:
            return None, "无法识别当前登录用户"

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
        except Exception as e:
            db.rollback()
            logger.error("批量审核冲次单价失败: %s", e)
            return None, str(e)
        return (
            StampingTonnagePriceBatchAuditResultVO(
                updated_count=updated,
                skipped_count=skipped,
                location=location,
                year=dto.year,
            ),
            None,
        )

    def batch_reverse_audit(
        self,
        db: Session,
        dto: StampingTonnagePriceBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> Tuple[Optional[StampingTonnagePriceBatchAuditResultVO], Optional[str]]:
        location = (dto.location or "").strip()
        if not location:
            return None, "请选择采购基地"
        remark = (dto.reverse_audit_remark or "").strip()
        if not remark:
            return None, "反审核原因必填"
        operator = display_name(current_user)
        if not operator:
            return None, "无法识别当前登录用户"

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
        except Exception as e:
            db.rollback()
            logger.error("批量反审核冲次单价失败: %s", e)
            return None, str(e)
        return (
            StampingTonnagePriceBatchAuditResultVO(
                updated_count=updated,
                skipped_count=skipped,
                location=location,
                year=dto.year,
            ),
            None,
        )

    def get_locations(self, db: Session) -> List[str]:
        return self.repository.get_distinct_locations(db)

    def get_years(self, db: Session) -> List[int]:
        return self.repository.get_distinct_years(db)

    def get_tonnages(self, db: Session) -> List[int]:
        return self.repository.get_distinct_tonnages(db)
