"""钢厂档案 Repository。"""

from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from app.models.masterdata.steel_mill import SteelMill, SteelMillAlias
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.steel_mill_dto import SteelMillInsert, SteelMillPatch


class SteelMillRepository:
    """钢厂与别名。头表不 relationship 别名，别名按 id 另查。"""

    def count(self, db: Session) -> int:
        return db.query(SteelMill).count()

    def get_by_id(self, db: Session, record_id: int) -> SteelMill | None:
        return db.query(SteelMill).filter(SteelMill.id == record_id).first()

    def max_sort_order(self, db: Session) -> int:
        value = db.query(SteelMill.sort_order).order_by(SteelMill.sort_order.desc()).first()
        if value is None:
            return 0
        return int(value[0])

    def list_all(self, db: Session) -> list[SteelMill]:
        return db.query(SteelMill).order_by(SteelMill.sort_order.asc(), SteelMill.id.asc()).all()

    def list_enabled(self, db: Session) -> list[SteelMill]:
        return (
            db.query(SteelMill)
            .filter(SteelMill.is_enabled.is_(True))
            .order_by(SteelMill.sort_order.asc(), SteelMill.id.asc())
            .all()
        )

    def list_aliases(self, db: Session) -> list[SteelMillAlias]:
        return db.query(SteelMillAlias).all()

    def aliases_for(self, db: Session, steel_mill_id: int) -> list[str]:
        rows = (
            db.query(SteelMillAlias.alias)
            .filter(SteelMillAlias.steel_mill_id == steel_mill_id)
            .order_by(SteelMillAlias.alias.asc())
            .all()
        )
        return [row[0] for row in rows]

    def aliases_by_mill(self, db: Session, mill_ids: list[int]) -> dict[int, list[str]]:
        if not mill_ids:
            return {}
        rows = (
            db.query(SteelMillAlias)
            .filter(SteelMillAlias.steel_mill_id.in_(mill_ids))
            .order_by(SteelMillAlias.alias.asc())
            .all()
        )
        grouped: dict[int, list[str]] = {mill_id: [] for mill_id in mill_ids}
        for row in rows:
            grouped.setdefault(row.steel_mill_id, []).append(row.alias)
        return grouped

    def paginate(
        self,
        db: Session,
        *,
        keyword: str | None,
        is_enabled: bool | None,
        skip: int,
        limit: int,
    ) -> tuple[list[SteelMill], int]:
        query = self._filtered(db, keyword=keyword, is_enabled=is_enabled)
        total = query.count()
        rows = (
            query.order_by(SteelMill.sort_order.asc(), SteelMill.id.asc())
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
    ) -> Query[SteelMill]:
        query = db.query(SteelMill)
        if is_enabled is not None:
            query = query.filter(SteelMill.is_enabled.is_(is_enabled))
        if keyword:
            like = f"%{keyword}%"
            alias_ids = db.query(SteelMillAlias.steel_mill_id).filter(
                SteelMillAlias.alias.like(like)
            )
            query = query.filter(
                or_(
                    SteelMill.abbreviation.like(like),
                    SteelMill.full_name.like(like),
                    SteelMill.id.in_(alias_ids),
                )
            )
        return query

    def create(self, db: Session, payload: SteelMillInsert) -> SteelMill:
        record = model_from_payload(SteelMill, payload)
        db.add(record)
        db.flush()
        db.refresh(record)
        return record

    def update(self, db: Session, record: SteelMill, payload: SteelMillPatch) -> SteelMill:
        apply_payload_fields(record, payload)
        db.flush()
        db.refresh(record)
        return record

    def replace_aliases(self, db: Session, steel_mill_id: int, aliases: list[str]) -> None:
        db.query(SteelMillAlias).filter(SteelMillAlias.steel_mill_id == steel_mill_id).delete(
            synchronize_session=False
        )
        for alias in aliases:
            db.add(SteelMillAlias(alias=alias, steel_mill_id=steel_mill_id))
        db.flush()

    def delete(self, db: Session, record: SteelMill) -> None:
        db.query(SteelMillAlias).filter(SteelMillAlias.steel_mill_id == record.id).delete(
            synchronize_session=False
        )
        db.delete(record)
        db.flush()
