"""计费管理 Repository。"""

from decimal import Decimal

from sqlalchemy import inspect, text
from sqlalchemy.orm import Query, Session, contains_eager

from app.models.masterdata.assembly_category import AssemblyCategory
from app.models.masterdata.category_billing import AssemblyCategoryBilling
from app.models.masterdata.fee_archive import FeeArchive
from app.repositories.persist import model_from_payload
from app.schemas.dto.category_billing_dto import AssemblyCategoryBillingInsert

_RETIRED_COLUMNS = ("sort_order", "is_enabled")


class AssemblyCategoryBillingRepository:
    """计费对照。读直接父表，不改父表。"""

    def drop_retired_columns(self, db: Session) -> bool:
        """旧库还有顺序、启用时删掉。新表直接返回。"""
        bind = db.get_bind()
        inspector = inspect(bind)
        table = AssemblyCategoryBilling.__tablename__
        if not inspector.has_table(table):
            return False
        present = {column["name"] for column in inspector.get_columns(table)}
        retired = [name for name in _RETIRED_COLUMNS if name in present]
        if not retired:
            return False
        for index in inspector.get_indexes(table):
            index_name = index.get("name")
            column_names = index.get("column_names") or []
            if index_name and any(name in column_names for name in retired):
                db.execute(text(f'DROP INDEX IF EXISTS "{index_name}"'))
        for name in retired:
            db.execute(text(f"ALTER TABLE {table} DROP COLUMN {name}"))
        return True

    def count(self, db: Session) -> int:
        return db.query(AssemblyCategoryBilling).count()

    def list_for_category(
        self,
        db: Session,
        assembly_category_id: int,
    ) -> list[AssemblyCategoryBilling]:
        """某个分类下的全部对照，按费用档案顺序。"""
        return (
            self._filtered(db, assembly_category_id=assembly_category_id)
            .order_by(
                FeeArchive.sort_order.asc(),
                FeeArchive.code.asc(),
                AssemblyCategoryBilling.id.asc(),
            )
            .all()
        )

    def paginate(
        self,
        db: Session,
        *,
        assembly_category_id: int | None,
        skip: int,
        limit: int,
    ) -> tuple[list[AssemblyCategoryBilling], int]:
        query = self._filtered(db, assembly_category_id=assembly_category_id)
        total = query.count()
        rows = (
            query.order_by(
                AssemblyCategory.sort_order.asc(),
                AssemblyCategory.code.asc(),
                FeeArchive.sort_order.asc(),
                FeeArchive.code.asc(),
                AssemblyCategoryBilling.id.asc(),
            )
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    def _filtered(
        self,
        db: Session,
        *,
        assembly_category_id: int | None,
    ) -> Query[AssemblyCategoryBilling]:
        query = (
            db.query(AssemblyCategoryBilling)
            .join(
                AssemblyCategory,
                AssemblyCategory.id == AssemblyCategoryBilling.assembly_category_id,
            )
            .join(FeeArchive, FeeArchive.id == AssemblyCategoryBilling.fee_archive_id)
            .options(
                contains_eager(AssemblyCategoryBilling.category),
                contains_eager(AssemblyCategoryBilling.fee),
            )
        )
        if assembly_category_id is not None:
            query = query.filter(
                AssemblyCategoryBilling.assembly_category_id == assembly_category_id
            )
        return query

    def list_enabled_checked_rates(
        self,
        db: Session,
        *,
        category_code: str | None = None,
    ) -> list[tuple[str, Decimal]]:
        """启用分类已勾选、且费用启用的计费率。指定分类时只读那一行。"""
        query = (
            db.query(FeeArchive.code, FeeArchive.charge_rate)
            .join(
                AssemblyCategoryBilling,
                AssemblyCategoryBilling.fee_archive_id == FeeArchive.id,
            )
            .join(
                AssemblyCategory,
                AssemblyCategory.id == AssemblyCategoryBilling.assembly_category_id,
            )
            .filter(AssemblyCategory.is_enabled.is_(True))
            .filter(FeeArchive.is_enabled.is_(True))
        )
        if category_code is not None:
            query = query.filter(AssemblyCategory.code == category_code)
        return [(str(code), Decimal(str(rate))) for code, rate in query.all()]

    def pair_exists(self, db: Session, category_id: int, fee_id: int) -> bool:
        found = (
            db.query(AssemblyCategoryBilling.id)
            .filter(
                AssemblyCategoryBilling.assembly_category_id == category_id,
                AssemblyCategoryBilling.fee_archive_id == fee_id,
            )
            .first()
        )
        return found is not None

    def create(
        self, db: Session, payload: AssemblyCategoryBillingInsert
    ) -> AssemblyCategoryBilling:
        record = model_from_payload(AssemblyCategoryBilling, payload)
        db.add(record)
        db.flush()
        return record

    def delete(self, db: Session, record: AssemblyCategoryBilling) -> None:
        db.delete(record)
        db.flush()
