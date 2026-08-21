"""
焊接工费单价 Service
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
from app.common.bom.welding_standard_process import validate_welding_unit_price_catalog
from app.common.timezone import now
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

logger = logging.getLogger("service.bom")


class BomWeldingUnitPriceService:
    """焊接工费单价业务逻辑"""

    def __init__(self) -> None:
        self.repository = BomWeldingUnitPriceRepository()

    def list_by_year(self, db: Session, year: int) -> List[BomWeldingUnitPriceResponse]:
        records = self.repository.list_by_year(db, year)
        return [BomWeldingUnitPriceResponse.model_validate(r) for r in records]

    def list_by_location_year(
        self, db: Session, location: str, year: int
    ) -> List[BomWeldingUnitPriceResponse]:
        records = self.repository.list_by_location_year(db, location, year)
        return [BomWeldingUnitPriceResponse.model_validate(r) for r in records]

    def list_all(self, db: Session) -> List[BomWeldingUnitPriceResponse]:
        records = self.repository.list_all(db)
        return [BomWeldingUnitPriceResponse.model_validate(r) for r in records]

    def paginate(
        self, db: Session, query: BomWeldingUnitPriceQuery
    ) -> Tuple[List[BomWeldingUnitPriceResponse], int, WeldingUnitPriceListFilters]:
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
        rows = [BomWeldingUnitPriceResponse.model_validate(r) for r in records]
        filters: WeldingUnitPriceListFilters = {
            "locations": self.repository.get_distinct_locations(db),
            "years": self.repository.get_distinct_years(db),
            "audit_status": audit_status,
            "summary": self.repository.summarize_by_filters(
                db,
                location=query.location,
                year=query.year,
                audit_status=audit_status,
            ),
        }
        return rows, total, filters

    def get_by_id(self, db: Session, id: int) -> Optional[BomWeldingUnitPriceResponse]:
        record = self.repository.get_by_id(db, id)
        if not record:
            return None
        return BomWeldingUnitPriceResponse.model_validate(record)

    def create(
        self,
        db: Session,
        data: BomWeldingUnitPriceCreate,
        current_user: UserVO,
    ) -> Tuple[Optional[BomWeldingUnitPriceResponse], Optional[str]]:
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
            return BomWeldingUnitPriceResponse.model_validate(record), None
        except IntegrityError:
            db.rollback()
            error_msg = (
                f"该基地({data.location})、年份({data.year})"
                f"和项目「{data.item_name}」的记录已存在"
            )
            logger.warning(error_msg)
            return None, error_msg
        except Exception as e:
            db.rollback()
            logger.error("创建焊接工费单价失败: %s", e)
            return None, str(e)

    def bulk_upsert(
        self,
        db: Session,
        items: List[BomWeldingUnitPriceCreate],
        current_user: UserVO,
    ) -> Tuple[
        List[BomWeldingUnitPriceResponse],
        List[BomWeldingUnitPriceResponse],
        List[str],
        int,
    ]:
        created: List[BomWeldingUnitPriceResponse] = []
        updated: List[BomWeldingUnitPriceResponse] = []
        failed: List[str] = []
        skipped_approved = 0

        for item in items:
            existing = self.repository.get_by_location_year_item(
                db, item.location, item.year, item.item_name
            )
            if existing:
                if existing.audit_status == AUDIT_APPROVED:
                    skipped_approved += 1
                    continue
                record, error = self.update(
                    db,
                    existing.id,
                    BomWeldingUnitPriceUpdate(
                        unit=item.unit,
                        unit_price=item.unit_price,
                        remark=item.remark,
                    ),
                    current_user=current_user,
                )
                if record:
                    updated.append(record)
                else:
                    failed.append(
                        error
                        or f"{item.location}/{item.year}/{item.item_name} 更新失败"
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
        data: BomWeldingUnitPriceUpdate,
        current_user: UserVO,
    ) -> Tuple[Optional[BomWeldingUnitPriceResponse], Optional[str]]:
        try:
            existing = self.repository.get_by_id(db, id)
            if not existing:
                return None, "记录不存在"
            if existing.audit_status == AUDIT_APPROVED:
                return None, "已审核通过，请先反审核后再修改"

            unit_to_check = data.unit if data.unit is not None else existing.unit
            try:
                validate_welding_unit_price_catalog(existing.item_name, unit_to_check)
            except ValueError as exc:
                return None, str(exc)

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
            return BomWeldingUnitPriceResponse.model_validate(record), None
        except Exception as e:
            db.rollback()
            logger.error("更新焊接工费单价失败: %s", e)
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
            logger.error("删除焊接工费单价失败: %s", e)
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
            logger.error("批量删除焊接工费单价失败: %s", e)
            return 0, 0, str(e)
        logger.info(
            "批量删除焊接工费单价: location=%s year=%s deleted=%s skipped=%s",
            location,
            year,
            deleted_count,
            skipped,
        )
        return deleted_count, skipped, None

    def batch_approve(
        self,
        db: Session,
        dto: BomWeldingUnitPriceBatchApproveDTO,
        current_user: UserVO,
    ) -> Tuple[Optional[BomWeldingUnitPriceBatchAuditResultVO], Optional[str]]:
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
            logger.error("批量审核焊接工费单价失败: %s", e)
            return None, str(e)
        return (
            BomWeldingUnitPriceBatchAuditResultVO(
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
        dto: BomWeldingUnitPriceBatchReverseAuditDTO,
        current_user: UserVO,
    ) -> Tuple[Optional[BomWeldingUnitPriceBatchAuditResultVO], Optional[str]]:
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
            logger.error("批量反审核焊接工费单价失败: %s", e)
            return None, str(e)
        return (
            BomWeldingUnitPriceBatchAuditResultVO(
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
