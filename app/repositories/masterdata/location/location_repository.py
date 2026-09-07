"""基地主数据 Repository。"""

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.masterdata.location import Location, LocationAlias
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.location_dto import LocationAliasInsert, LocationInsert, LocationPatch


class LocationRepository:
    """基地与别名数据访问。"""

    def count(self, db: Session) -> int:
        return db.query(Location).count()

    def get_by_location(self, db: Session, location: str) -> Location | None:
        return (
            db.query(Location)
            .options(joinedload(Location.aliases))
            .filter(Location.location == location)
            .first()
        )

    def get_alias(self, db: Session, alias: str) -> LocationAlias | None:
        return db.query(LocationAlias).filter(LocationAlias.alias == alias).first()

    def list_all(self, db: Session) -> list[Location]:
        return (
            db.query(Location)
            .options(joinedload(Location.aliases))
            .order_by(Location.sort_order.asc(), Location.location.asc())
            .all()
        )

    def list_enabled(self, db: Session) -> list[Location]:
        return (
            db.query(Location)
            .options(joinedload(Location.aliases))
            .filter(Location.is_enabled.is_(True))
            .order_by(Location.sort_order.asc(), Location.location.asc())
            .all()
        )

    def max_sort_order(self, db: Session) -> int:
        value = db.query(func.max(Location.sort_order)).scalar()
        return int(value or 0)

    def create(self, db: Session, payload: LocationInsert) -> Location:
        record = model_from_payload(Location, payload)
        db.add(record)
        db.flush()
        return record

    def apply_patch(
        self,
        db: Session,
        record: Location,
        patch: LocationPatch,
    ) -> Location:
        apply_payload_fields(record, patch)
        db.flush()
        return record

    def delete(self, db: Session, record: Location) -> None:
        db.delete(record)
        db.flush()

    def create_alias(self, db: Session, payload: LocationAliasInsert) -> LocationAlias:
        record = model_from_payload(LocationAlias, payload)
        db.add(record)
        db.flush()
        return record

    def delete_alias(self, db: Session, record: LocationAlias) -> None:
        db.delete(record)
        db.flush()
