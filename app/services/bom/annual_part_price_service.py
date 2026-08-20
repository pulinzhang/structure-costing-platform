"""
BOM 年度零件价 Service
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
    display_name,
)
from app.common.timezone import now
from app.repositories.bom.annual_part_price_repository import (
    AnnualPartPriceListFilters,
    BomAnnualPartPriceRepository,
)
from app.schemas.dto.bom_annual_part_price_dto import (
    BomAnnualPartPriceBatchApproveDTO,
    BomAnnualPartPriceBatchReverseAuditDTO,
    BomAnnualPartPriceCreate,
    BomAnnualPartPriceQuery,
    BomAnnualPartPriceUpdate,
)
from app.schemas.vo.bom_annual_part_price_vo import (
    BomAnnualPartPriceBatchAuditResultVO,
    BomAnnualPartPriceResponse,
)
from app.schemas.vo.user_vo import UserVO

logger = logging.getLogger("service.bom")


class BomAnnualPartPriceService:
    """年度零件价业务逻辑"""

    def __init__(self) -> None:
        self.repository = BomAnnualPartPriceRepository()

    def list_by_year(
        self, db: Session, year: int
    ) -> List[BomAnnualPartPriceResponse]:
        records = self.repository.list_by_year(db, year)
        return [BomAnnualPartPriceResponse.model_validate(r) for r in records]

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> List[BomAnnualPartPriceResponse]:
        records = self.repository.list_by_location_year(db, location, year)
        return [BomAnnualPartPriceResponse.model_validate(r) for r in records]

    def list_all(self, db: Session) -> List[BomAnnualPartPriceResponse]:
        records = self.repository.list_all(db)
        return [BomAnnualPartPriceResponse.model_validate(r) for r in records]

    def paginate(
        self, db: Session, query: BomAnnualPartPriceQuery
    ) -> Tuple[List[BomAnnualPartPriceResponse], int, AnnualPartPriceListFilters]:
        skip = (query.page - 1) * query.size
        audit_status = query.audit_status.strip() if query.audit_status else None
        keyword = query.keyword.strip() if query.keyword else None
        records, total = self.repository.paginate(
            db,
            location=query.location,
            year=query.year,
            audit_status=audit_status,
            keyword=keyword,
            skip=skip,
            limit=query.size,
        )
        rows = [BomAnnualPartPriceResponse.model_validate(r) for r in records]
        filters: AnnualPartPriceListFilters = {
            "locations": self.repository.get_distinct_locations(db),
            "years": self.repository.get_distinct_years(db),
            "audit_status": audit_status,
            "summary": self.repository.summarize_by_filters(
                db,
                location=query.location,
                year=query.year,
                audit_status=audit_status,
                keyword=keyword,
            ),
        }
        return rows, total, filters

    def get_by_id(
        self, db: Session, id: int
    ) -> Optional[BomAnnualPartPriceResponse]:
        record = self.repository.get_by_id(db, id)
        if not record:
            return None
        return BomAnnualPartPriceResponse.model_validate(record)

    def create(
        self,
        db: Session,
        data: BomAnnualPartPriceCreate,
        current_user: UserVO,
    ) -> Tuple[Optional[BomAnnualPartPriceResponse], Optional[str]]:
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
            return BomAnnualPartPriceResponse.model_validate(record), None
        except IntegrityError:
            db.rollback()
            error_msg = (
                f"该基地({data.location})、年份({data.year})"
                f"和零件「{data.part_number}」的记录已存在"
            )
            logger.warning(error_msg)
            return None, error_msg
        except Exception as e:
            db.rollback()
            logger.error("创建年度零件价失败: %s", e)
            return None, str(e)

    def update(
        self,
        db: Session,
        id: int,
        data: BomAnnualPartPriceUpdate,
        current_user: UserVO,
    ) -> Tuple[Optional[BomAnnualPartPriceResponse], Optional[str]]:
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
                updated_by=display_name(current_user),
            )
            if not record:
                return None, "记录不存在"
            db.commit()
            db.refresh(record)
            return BomAnnualPartPriceResponse.model_validate(record), None
        except Exception as e:
            db.rollback()
            logger.error("更新年度零件价失败: %s", e)
            return None, str(e)

    def delete(self, db: Session, id: int) -> Tuple[bool, Optional[str]]:
        try:
            record = self.repository.get_by_id(db, id)
            if not record:
                return False, "记录不存在"
            if record.audit_status == AUDIT_APPROVED:
                return False, "已审核通过，请先反审核后再删除"
            success = self.repository.delete(db, id)
            if not success:
                return False, "记录不存在"
            db.commit()
            return True, None
        except Exception as e:
            db.rollback()
            logger.error("删除年度零件价失败: %s", e)
            return False, str(e)

    def batch_delete_by_location_year(
        self,
        db: Session,
        *,
        location: str,
        year: int,
    ) -> Tuple[int, int, Optional[str]]:
        location = (location or "").strip()
        if not location:
            return 0, 0, "请选择采购基地"
        if year < 2000 or year > 2100:
            return 0, 0, "请选择正确的年度"

        existing = self.repository.list_by_location_year(db, location, year)
        if not existing:
            return 0, 0, f"基地「{location}」{year} 年没有可删除的数据"

        try:
            skipped = self.repository.count_by_location_year_and_statuses(
                db,
                location=location,
                year=year,
                statuses=[AUDIT_APPROVED],
            )
            deleted_count = self.repository.delete_unaudited_by_location_year(
                db, location, year
            )
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error("批量删除年度零件价失败: %s", e)
            return 0, 0, str(e)

        logger.info(
            "批量删除年度零件价: location=%s year=%s deleted=%s skipped=%s",
            location,
            year,
            deleted_count,
            skipped,
        )
        return deleted_count, skipped, None

    def batch_approve(
        self,
        db: Session,
        dto: BomAnnualPartPriceBatchApproveDTO,
        current_user: UserVO,
    ) -> Tuple[Optional[BomAnnualPartPriceBatchAuditResultVO], Optional[str]]:
        location = (dto.location or "").strip()
        if not location:
            return None, "请选择采购基地"
        operator = display_name(current_user)
        if not operator:
            return None, "无法识别当前登录用户"

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
        except Exception as e:
            db.rollback()
            logger.error("批量审核年度零件价失败: %s", e)
            return None, str(e)

        return (
            BomAnnualPartPriceBatchAuditResultVO(
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
        dto: BomAnnualPartPriceBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> Tuple[Optional[BomAnnualPartPriceBatchAuditResultVO], Optional[str]]:
        location = (dto.location or "").strip()
        if not location:
            return None, "请选择采购基地"
        remark = (dto.reverse_audit_remark or "").strip()
        if not remark:
            return None, "反审核原因必填"
        operator = display_name(current_user)
        if not operator:
            return None, "无法识别当前登录用户"

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
        except Exception as e:
            db.rollback()
            logger.error("批量反审核年度零件价失败: %s", e)
            return None, str(e)

        return (
            BomAnnualPartPriceBatchAuditResultVO(
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
