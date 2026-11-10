"""总成分类 Repository。"""

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models.masterdata.assembly_category import AssemblyCategory
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.assembly_category_dto import AssemblyCategoryInsert, AssemblyCategoryPatch


class AssemblyCategoryRepository:
    """总成分类。不查询计费表。"""

    def count(self, db: Session) -> int:
        return db.query(AssemblyCategory).count()

    def get_by_id(self, db: Session, record_id: int) -> AssemblyCategory | None:
        return db.query(AssemblyCategory).filter(AssemblyCategory.id == record_id).first()

    def get_by_code(self, db: Session, code: str) -> AssemblyCategory | None:
        return db.query(AssemblyCategory).filter(AssemblyCategory.code == code).first()

    def codes_by_ids(self, db: Session, category_ids: list[int]) -> dict[int, str]:
        if not category_ids:
            return {}
        rows = (
            db.query(AssemblyCategory.id, AssemblyCategory.code)
            .filter(AssemblyCategory.id.in_(category_ids))
            .all()
        )
        return {int(row.id): str(row.code) for row in rows}

    def list_enabled(self, db: Session) -> list[AssemblyCategory]:
        return (
            db.query(AssemblyCategory)
            .filter(AssemblyCategory.is_enabled.is_(True))
            .order_by(AssemblyCategory.sort_order.asc(), AssemblyCategory.id.asc())
            .all()
        )

    def get_by_name(self, db: Session, name: str) -> AssemblyCategory | None:
        return db.query(AssemblyCategory).filter(AssemblyCategory.name == name).first()

    def paginate(
        self,
        db: Session,
        *,
        keyword: str | None,
        is_enabled: bool | None,
        skip: int,
        limit: int,
    ) -> tuple[list[AssemblyCategory], int]:
        query = self._filtered(db, keyword=keyword, is_enabled=is_enabled)
        total = query.count()
        rows = (
            query.order_by(AssemblyCategory.sort_order.asc(), AssemblyCategory.code.asc())
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
    ) -> Query[AssemblyCategory]:
        query = db.query(AssemblyCategory)
        if is_enabled is not None:
            query = query.filter(AssemblyCategory.is_enabled.is_(is_enabled))
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(
                or_(AssemblyCategory.code.like(like), AssemblyCategory.name.like(like))
            )
        return query

    def create(self, db: Session, payload: AssemblyCategoryInsert) -> AssemblyCategory:
        record = model_from_payload(AssemblyCategory, payload)
        db.add(record)
        db.flush()
        db.refresh(record)
        return record

    def update(
        self,
        db: Session,
        record: AssemblyCategory,
        payload: AssemblyCategoryPatch,
    ) -> AssemblyCategory:
        apply_payload_fields(record, payload)
        db.flush()
        db.refresh(record)
        return record

    def delete(self, db: Session, record: AssemblyCategory) -> None:
        db.delete(record)
        db.flush()
