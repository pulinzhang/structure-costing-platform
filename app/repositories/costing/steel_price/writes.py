"""钢材价格写入：增删改、按期审核/反审、删未审。"""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING, AUDIT_REJECTED
from app.models.costing import SteelPrice
from app.repositories.costing.steel_price.queries import SteelPriceQueries
from app.repositories.persist import apply_payload_fields, model_from_payload, query_update
from app.schemas.dto.steel_price_dto import SteelPricePatch, SteelPriceWrite

logger = logging.getLogger("repository.steel_price")

_UPDATE_SKIP = frozenset({"id", "created_by", "created_at"})


class SteelPriceWrites:
    def __init__(self, queries: SteelPriceQueries | None = None) -> None:
        self._queries = queries or SteelPriceQueries()

    def create(self, db: Session, data: SteelPriceWrite) -> SteelPrice:
        """插入新记录。"""
        record = model_from_payload(SteelPrice, data)
        db.add(record)
        db.flush()
        logger.info(
            "创建钢材价格: year=%s month=%s location=%s grade=%s thickness=%s width=%s id=%s",
            data.year,
            data.month,
            data.location,
            data.grade,
            data.thickness,
            data.width,
            record.id,
        )
        return record

    def update(
        self,
        db: Session,
        record_id: int,
        update_data: SteelPriceWrite | SteelPricePatch,
    ) -> SteelPrice | None:
        """按主键更新记录，记录不存在时返回 None。"""
        record = self._queries.get_by_id(db, record_id)
        if record is None:
            return None
        apply_payload_fields(record, update_data, skip=_UPDATE_SKIP)
        db.flush()
        logger.info("更新钢材价格: id=%s", record_id)
        return record

    def delete(self, db: Session, record_id: int) -> bool:
        """按主键删除记录。"""
        record = self._queries.get_by_id(db, record_id)
        if record is None:
            return False
        db.delete(record)
        db.flush()
        logger.info("删除钢材价格: id=%s", record_id)
        return True

    def delete_unaudited_by_conditions(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        category_name: str | None = None,
        grade: str | None = None,
        steel_mill_id: int | None = None,
    ) -> int:
        """按条件批量删除未审核记录（pending / rejected），返回删除条数。"""
        query = self._queries._build_condition_query(
            db,
            year=year,
            month=month,
            location=location,
            category_name=category_name,
            grade=grade,
            steel_mill_id=steel_mill_id,
        ).filter(SteelPrice.audit_status != AUDIT_APPROVED)
        deleted_count = query.delete(synchronize_session=False)
        db.flush()
        logger.info(
            "批量删除未审核钢材价格: year=%s month=%s location=%s count=%s",
            year,
            month,
            location,
            deleted_count,
        )
        return deleted_count

    def approve_by_period(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
        updated_by: str | None = None,
    ) -> int:
        """批量审核通过：pending/rejected → approved。返回更新条数。"""
        query = self._queries._build_condition_query(
            db,
            year=year,
            month=month,
            location=location,
        ).filter(SteelPrice.audit_status.in_([AUDIT_PENDING, AUDIT_REJECTED]))
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_APPROVED,
            "audited_by": audited_by,
            "audited_at": audited_at,
            "audit_remark": audit_remark,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by
        updated_count = query_update(query, values)
        db.flush()
        logger.info(
            "批量审核通过: year=%s month=%s location=%s count=%s",
            year,
            month,
            location,
            updated_count,
        )
        return int(updated_count or 0)

    def reverse_audit_by_period(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: str | None = None,
    ) -> int:
        """批量反审核：approved → pending。返回更新条数。"""
        query = self._queries._build_condition_query(
            db,
            year=year,
            month=month,
            location=location,
        ).filter(SteelPrice.audit_status == AUDIT_APPROVED)
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_PENDING,
            "reverse_audited_by": reverse_audited_by,
            "reverse_audited_at": reverse_audited_at,
            "reverse_audit_remark": reverse_audit_remark,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by
        updated_count = query_update(query, values)
        db.flush()
        logger.info(
            "批量反审核: year=%s month=%s location=%s count=%s",
            year,
            month,
            location,
            updated_count,
        )
        return int(updated_count or 0)
