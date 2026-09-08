"""供应商主数据 Repository。"""

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.masterdata.supplier import Supplier, SupplierAlias
from app.repositories.persist import apply_payload_fields, model_from_payload
from app.schemas.dto.supplier_dto import SupplierAliasInsert, SupplierInsert, SupplierPatch


class SupplierRepository:
    """供应商与别名数据访问。"""

    def get_by_full_name(self, db: Session, full_name: str) -> Supplier | None:
        return (
            db.query(Supplier)
            .options(joinedload(Supplier.aliases))
            .filter(Supplier.full_name == full_name)
            .first()
        )

    def get_by_abbreviation(self, db: Session, abbreviation: str) -> Supplier | None:
        return (
            db.query(Supplier)
            .options(joinedload(Supplier.aliases))
            .filter(Supplier.abbreviation == abbreviation)
            .first()
        )

    def get_by_erp_code(self, db: Session, erp_code: str) -> Supplier | None:
        return (
            db.query(Supplier)
            .options(joinedload(Supplier.aliases))
            .filter(Supplier.erp_code == erp_code)
            .first()
        )

    def get_alias(self, db: Session, alias: str) -> SupplierAlias | None:
        return db.query(SupplierAlias).filter(SupplierAlias.alias == alias).first()

    def list_all(self, db: Session) -> list[Supplier]:
        return (
            db.query(Supplier)
            .options(joinedload(Supplier.aliases))
            .order_by(Supplier.sort_order.asc(), Supplier.full_name.asc())
            .all()
        )

    def list_enabled(self, db: Session) -> list[Supplier]:
        return (
            db.query(Supplier)
            .options(joinedload(Supplier.aliases))
            .filter(Supplier.is_enabled.is_(True))
            .order_by(Supplier.sort_order.asc(), Supplier.full_name.asc())
            .all()
        )

    def paginate(
        self,
        db: Session,
        *,
        keyword: str | None,
        is_enabled: bool | None,
        skip: int,
        limit: int,
    ) -> tuple[list[Supplier], int]:
        q = db.query(Supplier)
        if is_enabled is not None:
            q = q.filter(Supplier.is_enabled.is_(is_enabled))
        if keyword:
            like = f"%{keyword}%"
            alias_full_names = db.query(SupplierAlias.full_name).filter(
                SupplierAlias.alias.like(like)
            )
            q = q.filter(
                or_(
                    Supplier.abbreviation.like(like),
                    Supplier.full_name.like(like),
                    Supplier.erp_code.like(like),
                    Supplier.full_name.in_(alias_full_names),
                )
            )
        total = q.count()
        rows = (
            q.options(joinedload(Supplier.aliases))
            .order_by(Supplier.sort_order.asc(), Supplier.full_name.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def list_for_export(
        self,
        db: Session,
        *,
        keyword: str | None,
        is_enabled: bool | None,
    ) -> list[Supplier]:
        q = db.query(Supplier)
        if is_enabled is not None:
            q = q.filter(Supplier.is_enabled.is_(is_enabled))
        if keyword:
            like = f"%{keyword}%"
            alias_full_names = db.query(SupplierAlias.full_name).filter(
                SupplierAlias.alias.like(like)
            )
            q = q.filter(
                or_(
                    Supplier.abbreviation.like(like),
                    Supplier.full_name.like(like),
                    Supplier.erp_code.like(like),
                    Supplier.full_name.in_(alias_full_names),
                )
            )
        return (
            q.options(joinedload(Supplier.aliases))
            .order_by(Supplier.sort_order.asc(), Supplier.full_name.asc())
            .all()
        )

    def max_sort_order(self, db: Session) -> int:
        value = db.query(func.max(Supplier.sort_order)).scalar()
        return int(value or 0)

    def create(self, db: Session, payload: SupplierInsert) -> Supplier:
        record = model_from_payload(Supplier, payload)
        db.add(record)
        db.flush()
        return record

    def apply_patch(
        self,
        db: Session,
        record: Supplier,
        patch: SupplierPatch,
    ) -> Supplier:
        apply_payload_fields(record, patch)
        db.flush()
        return record

    def create_alias(self, db: Session, payload: SupplierAliasInsert) -> SupplierAlias:
        record = model_from_payload(SupplierAlias, payload)
        db.add(record)
        db.flush()
        return record

    def delete_alias(self, db: Session, record: SupplierAlias) -> None:
        db.delete(record)
        db.flush()
