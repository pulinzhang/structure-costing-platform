"""
BOM 包装运输费 Repository
只负责查询构建与会话写入（flush），禁止 commit/rollback。
"""

import logging
from datetime import datetime
from typing import TypedDict

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Query, Session

from app.common.audit import AUDIT_APPROVED, AUDIT_PENDING
from app.models.bom.packaging_transport_fee import BomPackagingTransportFee
from app.repositories.persist import apply_dto_fields, model_from_payload, query_update
from app.schemas.dto.bom_packaging_transport_fee_dto import (
    BomPackagingTransportFeeCreate,
    BomPackagingTransportFeeUpdate,
)

logger = logging.getLogger("repository.bom")


class AuditCountSummary(TypedDict):
    total_count: int
    pending_count: int
    approved_count: int


class PackagingTransportFeeListFilters(TypedDict):
    locations: list[str]
    years: list[int]
    vehicle_models: list[str]
    audit_status: str | None
    summary: AuditCountSummary


class BomPackagingTransportFeeRepository:
    """包装运输费数据访问"""

    def get_by_id(self, db: Session, id: int) -> BomPackagingTransportFee | None:
        return db.query(BomPackagingTransportFee).filter(BomPackagingTransportFee.id == id).first()

    def get_by_unique_key(
        self,
        db: Session,
        location: str,
        year: int,
        vehicle_model: str,
        part_number: str,
    ) -> BomPackagingTransportFee | None:
        return (
            db.query(BomPackagingTransportFee)
            .filter(
                and_(
                    BomPackagingTransportFee.location == location,
                    BomPackagingTransportFee.year == year,
                    BomPackagingTransportFee.vehicle_model == vehicle_model,
                    BomPackagingTransportFee.part_number == part_number,
                )
            )
            .first()
        )

    def list_by_scope(
        self,
        db: Session,
        location: str,
        year: int,
        vehicle_model: str,
    ) -> list[BomPackagingTransportFee]:
        return (
            db.query(BomPackagingTransportFee)
            .filter(
                and_(
                    BomPackagingTransportFee.location == location,
                    BomPackagingTransportFee.year == year,
                    BomPackagingTransportFee.vehicle_model == vehicle_model,
                )
            )
            .order_by(BomPackagingTransportFee.part_number)
            .all()
        )

    def count_by_location_year(self, db: Session, *, location: str, year: int) -> int:
        return (
            db.query(BomPackagingTransportFee)
            .filter(
                BomPackagingTransportFee.location == location,
                BomPackagingTransportFee.year == year,
            )
            .count()
        )

    def list_by_location_year(
        self, db: Session, *, location: str, year: int
    ) -> list[BomPackagingTransportFee]:
        return (
            db.query(BomPackagingTransportFee)
            .filter(
                BomPackagingTransportFee.location == location,
                BomPackagingTransportFee.year == year,
            )
            .order_by(BomPackagingTransportFee.part_number)
            .all()
        )

    def _build_list_query(
        self,
        db: Session,
        location: str | None = None,
        year: int | None = None,
        vehicle_model: str | None = None,
        audit_status: str | None = None,
        keyword: str | None = None,
    ) -> Query[BomPackagingTransportFee]:
        q = db.query(BomPackagingTransportFee)
        if location is not None:
            q = q.filter(BomPackagingTransportFee.location == location)
        if year is not None:
            q = q.filter(BomPackagingTransportFee.year == year)
        if vehicle_model is not None:
            q = q.filter(BomPackagingTransportFee.vehicle_model == vehicle_model)
        if audit_status:
            q = q.filter(BomPackagingTransportFee.audit_status == audit_status)
        if keyword:
            pattern = f"%{keyword}%"
            q = q.filter(
                or_(
                    BomPackagingTransportFee.part_number.like(pattern),
                    BomPackagingTransportFee.part_name.like(pattern),
                )
            )
        return q

    def paginate(
        self,
        db: Session,
        location: str | None = None,
        year: int | None = None,
        vehicle_model: str | None = None,
        audit_status: str | None = None,
        keyword: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[BomPackagingTransportFee], int]:
        q = self._build_list_query(
            db,
            location=location,
            year=year,
            vehicle_model=vehicle_model,
            audit_status=audit_status,
            keyword=keyword,
        )
        total = q.count()
        records = (
            q.order_by(
                BomPackagingTransportFee.location,
                BomPackagingTransportFee.year,
                BomPackagingTransportFee.vehicle_model,
                BomPackagingTransportFee.part_number,
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total

    def summarize_by_filters(
        self,
        db: Session,
        location: str | None = None,
        year: int | None = None,
        vehicle_model: str | None = None,
        audit_status: str | None = None,
        keyword: str | None = None,
    ) -> AuditCountSummary:
        q = self._build_list_query(
            db,
            location=location,
            year=year,
            vehicle_model=vehicle_model,
            audit_status=audit_status,
            keyword=keyword,
        )
        row = q.with_entities(
            func.count(BomPackagingTransportFee.id).label("total_count"),
            func.sum(
                case(
                    (BomPackagingTransportFee.audit_status == AUDIT_PENDING, 1),
                    else_=0,
                )
            ).label("pending_count"),
            func.sum(
                case(
                    (BomPackagingTransportFee.audit_status == AUDIT_APPROVED, 1),
                    else_=0,
                )
            ).label("approved_count"),
        ).one()
        return {
            "total_count": int(row.total_count or 0),
            "pending_count": int(row.pending_count or 0),
            "approved_count": int(row.approved_count or 0),
        }

    def list_for_export(
        self,
        db: Session,
        location: str | None = None,
        year: int | None = None,
        vehicle_model: str | None = None,
        audit_status: str | None = None,
        keyword: str | None = None,
    ) -> list[BomPackagingTransportFee]:
        q = self._build_list_query(
            db,
            location=location,
            year=year,
            vehicle_model=vehicle_model,
            audit_status=audit_status,
            keyword=keyword,
        )
        return q.order_by(
            BomPackagingTransportFee.location,
            BomPackagingTransportFee.year,
            BomPackagingTransportFee.vehicle_model,
            BomPackagingTransportFee.part_number,
        ).all()

    def get_distinct_locations(self, db: Session) -> list[str]:
        results = (
            db.query(BomPackagingTransportFee.location)
            .distinct()
            .order_by(BomPackagingTransportFee.location)
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_years(self, db: Session) -> list[int]:
        results = (
            db.query(BomPackagingTransportFee.year)
            .distinct()
            .order_by(BomPackagingTransportFee.year.desc())
            .all()
        )
        return [r[0] for r in results]

    def get_distinct_vehicle_models(self, db: Session) -> list[str]:
        results = (
            db.query(BomPackagingTransportFee.vehicle_model)
            .distinct()
            .order_by(BomPackagingTransportFee.vehicle_model)
            .all()
        )
        return [r[0] for r in results]

    def count_by_scope_and_statuses(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        vehicle_model: str,
        statuses: list[str],
    ) -> int:
        return (
            db.query(BomPackagingTransportFee)
            .filter(
                BomPackagingTransportFee.location == location,
                BomPackagingTransportFee.year == year,
                BomPackagingTransportFee.vehicle_model == vehicle_model,
                BomPackagingTransportFee.audit_status.in_(statuses),
            )
            .count()
        )

    def create(
        self,
        db: Session,
        data: BomPackagingTransportFeeCreate,
        *,
        created_by: str,
        updated_by: str,
    ) -> BomPackagingTransportFee:
        record = model_from_payload(BomPackagingTransportFee, data)
        record.created_by = created_by
        record.updated_by = updated_by
        record.audit_status = AUDIT_PENDING
        db.add(record)
        db.flush()
        db.refresh(record)
        logger.info(
            "创建包装运输费: location=%s year=%s vehicle=%s part=%s id=%s",
            data.location,
            data.year,
            data.vehicle_model,
            data.part_number,
            record.id,
        )
        return record

    def update(
        self,
        db: Session,
        id: int,
        update_data: BomPackagingTransportFeeUpdate,
        *,
        updated_by: str,
    ) -> BomPackagingTransportFee | None:
        record = self.get_by_id(db, id)
        if not record:
            return None
        apply_dto_fields(record, update_data)
        record.updated_by = updated_by
        db.flush()
        db.refresh(record)
        logger.info("更新包装运输费: id=%s", id)
        return record

    def delete(self, db: Session, id: int) -> bool:
        record = self.get_by_id(db, id)
        if not record:
            return False
        db.delete(record)
        db.flush()
        logger.info("删除包装运输费: id=%s", id)
        return True

    def delete_unaudited_by_scope(
        self,
        db: Session,
        location: str,
        year: int,
        vehicle_model: str,
    ) -> int:
        count = (
            db.query(BomPackagingTransportFee)
            .filter(
                BomPackagingTransportFee.location == location,
                BomPackagingTransportFee.year == year,
                BomPackagingTransportFee.vehicle_model == vehicle_model,
                BomPackagingTransportFee.audit_status != AUDIT_APPROVED,
            )
            .delete(synchronize_session=False)
        )
        db.flush()
        logger.info(
            "删除未审核包装运输费: location=%s year=%s vehicle=%s count=%s",
            location,
            year,
            vehicle_model,
            count,
        )
        return count

    def approve_by_scope(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        vehicle_model: str,
        audited_by: str,
        audited_at: datetime,
        audit_remark: str | None,
        updated_by: str | None = None,
    ) -> int:
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_APPROVED,
            "audited_by": audited_by,
            "audited_at": audited_at,
            "audit_remark": audit_remark,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by
        count = query_update(
            db.query(BomPackagingTransportFee).filter(
                BomPackagingTransportFee.location == location,
                BomPackagingTransportFee.year == year,
                BomPackagingTransportFee.vehicle_model == vehicle_model,
                BomPackagingTransportFee.audit_status == AUDIT_PENDING,
            ),
            values,
        )
        db.flush()
        return count

    def reverse_by_scope(
        self,
        db: Session,
        *,
        location: str,
        year: int,
        vehicle_model: str,
        reverse_audited_by: str,
        reverse_audited_at: datetime,
        reverse_audit_remark: str,
        updated_by: str | None = None,
    ) -> int:
        values: dict[str, str | datetime | None] = {
            "audit_status": AUDIT_PENDING,
            "reverse_audited_by": reverse_audited_by,
            "reverse_audited_at": reverse_audited_at,
            "reverse_audit_remark": reverse_audit_remark,
        }
        if updated_by is not None:
            values["updated_by"] = updated_by
        count = query_update(
            db.query(BomPackagingTransportFee).filter(
                BomPackagingTransportFee.location == location,
                BomPackagingTransportFee.year == year,
                BomPackagingTransportFee.vehicle_model == vehicle_model,
                BomPackagingTransportFee.audit_status == AUDIT_APPROVED,
            ),
            values,
        )
        db.flush()
        return count
