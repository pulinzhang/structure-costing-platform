"""费用档案 Repository。"""

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models.masterdata.fee_archive import FeeArchive
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.fee_archive_dto import FeeArchiveInsert, FeeArchivePatch


class FeeArchiveRepository:
    """费用档案。不查询计费表。"""

    def count(self, db: Session) -> int:
        return db.query(FeeArchive).count()

    def get_by_id(self, db: Session, record_id: int) -> FeeArchive | None:
        return db.query(FeeArchive).filter(FeeArchive.id == record_id).first()

    def get_by_code(self, db: Session, code: str) -> FeeArchive | None:
        return db.query(FeeArchive).filter(FeeArchive.code == code).first()

    def get_by_name(self, db: Session, name: str) -> FeeArchive | None:
        return db.query(FeeArchive).filter(FeeArchive.name == name).first()

    def paginate(
        self,
        db: Session,
        *,
        keyword: str | None,
        is_enabled: bool | None,
        skip: int,
        limit: int,
    ) -> tuple[list[FeeArchive], int]:
        query = self._filtered(db, keyword=keyword, is_enabled=is_enabled)
        total = query.count()
        rows = (
            query.order_by(FeeArchive.sort_order.asc(), FeeArchive.code.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def _filtered(
        self,
        db: Session,
        *,
        keyword: str | None,
        is_enabled: bool | None,
    ) -> Query[FeeArchive]:
        query = db.query(FeeArchive)
        if is_enabled is not None:
            query = query.filter(FeeArchive.is_enabled.is_(is_enabled))
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(FeeArchive.code.like(like), FeeArchive.name.like(like)))
        return query

    def create(self, db: Session, payload: FeeArchiveInsert) -> FeeArchive:
        record = model_from_payload(FeeArchive, payload)
        db.add(record)
        db.flush()
        db.refresh(record)
        return record

    def update(self, db: Session, record: FeeArchive, payload: FeeArchivePatch) -> FeeArchive:
        apply_payload_fields(record, payload)
        db.flush()
        db.refresh(record)
        return record

    def delete(self, db: Session, record: FeeArchive) -> None:
        db.delete(record)
        db.flush()
