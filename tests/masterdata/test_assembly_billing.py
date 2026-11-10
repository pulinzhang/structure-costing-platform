"""总成分类、费用档案、计费管理。"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.audit import SYSTEM_USER
from app.database import Base
from app.exceptions.base import BusinessException, NotFoundException
from app.models.masterdata.assembly_category import AssemblyCategory
from app.models.masterdata.category_billing import AssemblyCategoryBilling
from app.models.masterdata.fee_archive import FeeArchive
from app.models.settings.ref_hint import RefHint
from app.models.settings.schema_comment import SchemaComment
from app.schemas.dto.assembly_category_dto import (
    AssemblyCategoryCreate,
    AssemblyCategoryQuery,
    AssemblyCategoryUpdate,
)
from app.schemas.dto.category_billing_dto import (
    AssemblyCategoryBillingQuery,
    CategoryBillingReplace,
)
from app.schemas.dto.fee_archive_dto import FeeArchiveCreate, FeeArchiveQuery, FeeArchiveUpdate
from app.services.masterdata.assembly_category.seed import ASSEMBLY_CATEGORY_SEEDS
from app.services.masterdata.assembly_category.service import AssemblyCategoryService
from app.services.masterdata.category_billing.seed import BILLING_SEED_PAIRS
from app.services.masterdata.category_billing.service import AssemblyCategoryBillingService
from app.services.masterdata.fee_archive.seed import FEE_ARCHIVE_SEEDS
from app.services.masterdata.fee_archive.service import FeeArchiveService
from app.services.settings.schema_comment.seed import ensure_schema_reference_seed
from app.services.settings.schema_comment.service import STILL_REFERENCED


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(
        bind=engine,
        tables=[
            SchemaComment.__table__,
            RefHint.__table__,
            AssemblyCategory.__table__,
            FeeArchive.__table__,
            AssemblyCategoryBilling.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()
    try:
        ensure_schema_reference_seed(session)
        yield session
    finally:
        session.close()
        engine.dispose()


def test_seed_writes_catalog_once(memory_db: Session) -> None:
    AssemblyCategoryService().ensure_seed_if_empty(memory_db)
    FeeArchiveService().ensure_seed_if_empty(memory_db)
    categories, category_total = AssemblyCategoryService().list_page(
        memory_db, AssemblyCategoryQuery(page=1, size=20)
    )
    fees, fee_total = FeeArchiveService().list_page(memory_db, FeeArchiveQuery(page=1, size=20))
    assert category_total == len(ASSEMBLY_CATEGORY_SEEDS)
    assert [row.name for row in categories] == ["冲压件", "凸焊件", "总成件", "黑漆件"]
    assert fee_total == len(FEE_ARCHIVE_SEEDS)
    assert fees[0].model_dump()["charge_rate"] == "0.010000"
    assert fees[2].model_dump()["charge_rate"] == "0.020000"
    transport = next(row for row in fees if row.code == "transport")
    FeeArchiveService().update(
        memory_db,
        transport.id,
        FeeArchiveUpdate(
            name=transport.name,
            charge_basis=transport.charge_basis,
            charge_rate=Decimal("0.03"),
            sort_order=transport.sort_order,
            is_enabled=True,
        ),
        SYSTEM_USER,
    )
    FeeArchiveService().ensure_seed_if_empty(memory_db)
    again, _total = FeeArchiveService().list_page(memory_db, FeeArchiveQuery(page=1, size=20))
    kept = next(row for row in again if row.code == "transport")
    assert kept.model_dump()["charge_rate"] == "0.030000"


def test_billing_seed_checks_live_fees_for_every_category(memory_db: Session) -> None:
    AssemblyCategoryService().ensure_seed_if_empty(memory_db)
    FeeArchiveService().ensure_seed_if_empty(memory_db)
    billing = AssemblyCategoryBillingService()
    billing.ensure_seed_if_empty(memory_db)
    rows, total = billing.list_page(memory_db, AssemblyCategoryBillingQuery(page=1, size=100))
    assert total == len(BILLING_SEED_PAIRS)
    by_category: dict[str, list[str]] = {}
    for row in rows:
        by_category.setdefault(row.assembly_category_code, []).append(row.fee_code)
    expected_fees = [fee.code for fee in FEE_ARCHIVE_SEEDS]
    for category in ASSEMBLY_CATEGORY_SEEDS:
        assert by_category[category.code] == expected_fees
    billing.ensure_seed_if_empty(memory_db)
    _again, again_total = billing.list_page(
        memory_db, AssemblyCategoryBillingQuery(page=1, size=100)
    )
    assert again_total == total
    categories, _category_total = AssemblyCategoryService().list_page(
        memory_db, AssemblyCategoryQuery(page=1, size=20)
    )
    fees, _fee_total = FeeArchiveService().list_page(memory_db, FeeArchiveQuery(page=1, size=20))
    billing.replace_selection(
        memory_db,
        categories[0].id,
        CategoryBillingReplace(fee_archive_ids=[fees[0].id]),
        SYSTEM_USER,
    )
    billing.ensure_seed_if_empty(memory_db)
    _kept, kept_total = billing.list_page(
        memory_db,
        AssemblyCategoryBillingQuery(assembly_category_id=categories[0].id, page=1, size=20),
    )
    assert kept_total == 1


def test_code_is_normalized_and_name_is_unique(memory_db: Session) -> None:
    with pytest.raises(ValidationError):
        AssemblyCategoryCreate(code="冲压", name="甲", sort_order=1)
    created = AssemblyCategoryService().create(
        memory_db,
        AssemblyCategoryCreate(code="New_Kind", name=" 新分类 ", sort_order=9),
        SYSTEM_USER,
    )
    assert created.code == "new_kind"
    assert created.name == "新分类"
    with pytest.raises(BusinessException) as duplicated:
        AssemblyCategoryService().create(
            memory_db,
            AssemblyCategoryCreate(code="other", name="新分类", sort_order=10),
            SYSTEM_USER,
        )
    assert duplicated.value.code == 409


def test_fee_rate_rejects_over_100_percent() -> None:
    with pytest.raises(ValidationError):
        FeeArchiveCreate(
            code="extra",
            name="额外",
            charge_basis="rate",
            charge_rate="2",
            sort_order=1,
        )


def test_delete_category_is_blocked_while_billing_exists(memory_db: Session) -> None:
    AssemblyCategoryService().ensure_seed_if_empty(memory_db)
    FeeArchiveService().ensure_seed_if_empty(memory_db)
    categories, _category_total = AssemblyCategoryService().list_page(
        memory_db, AssemblyCategoryQuery(page=1, size=20)
    )
    fees, _fee_total = FeeArchiveService().list_page(memory_db, FeeArchiveQuery(page=1, size=20))
    stamping = categories[0]
    fee = fees[0]
    billing = AssemblyCategoryBillingService()
    billing.replace_selection(
        memory_db,
        stamping.id,
        CategoryBillingReplace(fee_archive_ids=[fee.id]),
        SYSTEM_USER,
    )
    listed, billing_total = billing.list_page(
        memory_db,
        AssemblyCategoryBillingQuery(assembly_category_id=stamping.id, page=1, size=10),
    )
    assert billing_total == 1
    assert listed[0].assembly_category_name == stamping.name
    with pytest.raises(BusinessException) as blocked:
        AssemblyCategoryService().delete(memory_db, stamping.id)
    assert blocked.value.message == STILL_REFERENCED
    assert blocked.value.audit_detail is not None
    assert "计费管理" in blocked.value.audit_detail
    billing.replace_selection(
        memory_db,
        stamping.id,
        CategoryBillingReplace(fee_archive_ids=[]),
        SYSTEM_USER,
    )
    AssemblyCategoryService().delete(memory_db, stamping.id)
    remaining, total = AssemblyCategoryService().list_page(
        memory_db, AssemblyCategoryQuery(page=1, size=20)
    )
    assert total == 3
    assert all(item.id != stamping.id for item in remaining)


def test_replace_selection_saves_checks_for_one_category(memory_db: Session) -> None:
    AssemblyCategoryService().ensure_seed_if_empty(memory_db)
    FeeArchiveService().ensure_seed_if_empty(memory_db)
    categories, _category_total = AssemblyCategoryService().list_page(
        memory_db, AssemblyCategoryQuery(page=1, size=20)
    )
    fees, _fee_total = FeeArchiveService().list_page(memory_db, FeeArchiveQuery(page=1, size=20))
    stamping = next(row for row in categories if row.code == "stamping")
    assembly = next(row for row in categories if row.code == "assembly")
    transport = next(row for row in fees if row.code == "transport")
    management = next(row for row in fees if row.code == "management")
    billing = AssemblyCategoryBillingService()

    with pytest.raises(ValidationError):
        CategoryBillingReplace(fee_archive_ids=[transport.id, transport.id])
    with pytest.raises(NotFoundException, match="费用档案不存在"):
        billing.replace_selection(
            memory_db,
            stamping.id,
            CategoryBillingReplace(fee_archive_ids=[999999]),
            SYSTEM_USER,
        )

    saved = billing.replace_selection(
        memory_db,
        stamping.id,
        CategoryBillingReplace(fee_archive_ids=[management.id, transport.id]),
        SYSTEM_USER,
    )
    assert saved.assembly_category_name == "冲压件"
    assert [item.fee_code for item in saved.items] == ["transport", "management"]
    assert saved.items[0].model_dump()["charge_rate"] == "0.020000"
    assert saved.items[0].remark is None
    memory_db.execute(
        text(
            "UPDATE assembly_category_billings SET remark = :remark WHERE fee_archive_id = :fee_id"
        ),
        {"remark": "keep", "fee_id": management.id},
    )
    memory_db.commit()

    FeeArchiveService().update(
        memory_db,
        management.id,
        FeeArchiveUpdate(
            name=management.name,
            charge_basis=management.charge_basis,
            charge_rate=management.charge_rate,
            sort_order=management.sort_order,
            is_enabled=False,
        ),
        SYSTEM_USER,
    )
    kept = billing.replace_selection(
        memory_db,
        stamping.id,
        CategoryBillingReplace(fee_archive_ids=[management.id]),
        SYSTEM_USER,
    )
    assert [item.fee_code for item in kept.items] == ["management"]
    assert kept.items[0].remark == "keep"
    FeeArchiveService().update(
        memory_db,
        transport.id,
        FeeArchiveUpdate(
            name=transport.name,
            charge_basis=transport.charge_basis,
            charge_rate=transport.charge_rate,
            sort_order=transport.sort_order,
            is_enabled=False,
        ),
        SYSTEM_USER,
    )
    with pytest.raises(BusinessException, match="费用已停用"):
        billing.replace_selection(
            memory_db,
            stamping.id,
            CategoryBillingReplace(fee_archive_ids=[management.id, transport.id]),
            SYSTEM_USER,
        )

    AssemblyCategoryService().update(
        memory_db,
        assembly.id,
        AssemblyCategoryUpdate(
            name=assembly.name, sort_order=assembly.sort_order, is_enabled=False
        ),
        SYSTEM_USER,
    )
    with pytest.raises(BusinessException, match="分类已停用"):
        billing.replace_selection(
            memory_db,
            assembly.id,
            CategoryBillingReplace(fee_archive_ids=[transport.id]),
            SYSTEM_USER,
        )

    cleared = billing.replace_selection(
        memory_db,
        stamping.id,
        CategoryBillingReplace(fee_archive_ids=[]),
        SYSTEM_USER,
    )
    assert cleared.items == []
    _rows, total = billing.list_page(
        memory_db, AssemblyCategoryBillingQuery(assembly_category_id=stamping.id, page=1, size=10)
    )
    assert total == 0


def test_category_update_keeps_code(memory_db: Session) -> None:
    created = AssemblyCategoryService().create(
        memory_db,
        AssemblyCategoryCreate(code="paint", name="涂装件", sort_order=8),
        SYSTEM_USER,
    )
    updated = AssemblyCategoryService().update(
        memory_db,
        created.id,
        AssemblyCategoryUpdate(name="涂装", sort_order=8, is_enabled=False),
        SYSTEM_USER,
    )
    assert updated.code == "paint"
    assert updated.name == "涂装"
    assert updated.is_enabled is False
    listed, total = AssemblyCategoryBillingService().list_page(
        memory_db, AssemblyCategoryBillingQuery(page=1, size=10)
    )
    assert total == 0
    assert listed == []


def test_retired_billing_columns_are_dropped() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE assembly_category_billings (
                    id INTEGER PRIMARY KEY,
                    assembly_category_id INTEGER NOT NULL,
                    fee_archive_id INTEGER NOT NULL,
                    sort_order INTEGER NOT NULL,
                    is_enabled BOOLEAN NOT NULL,
                    remark TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                "CREATE INDEX ix_assembly_category_billing_sort "
                "ON assembly_category_billings (sort_order)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO assembly_category_billings "
                "(assembly_category_id, fee_archive_id, sort_order, is_enabled, remark) "
                "VALUES (1, 2, 3, 1, 'keep')"
            )
        )
    session = sessionmaker(bind=engine)()
    try:
        AssemblyCategoryBillingService().drop_retired_columns(session)
        columns = {
            row[1] for row in session.execute(text("PRAGMA table_info(assembly_category_billings)"))
        }
        assert "sort_order" not in columns
        assert "is_enabled" not in columns
        assert (
            session.execute(text("SELECT remark FROM assembly_category_billings")).scalar()
            == "keep"
        )
        AssemblyCategoryBillingService().drop_retired_columns(session)
    finally:
        session.close()
        engine.dispose()


def test_finished_fee_rates_follow_checked_fees(memory_db: Session) -> None:
    AssemblyCategoryService().ensure_seed_if_empty(memory_db)
    FeeArchiveService().ensure_seed_if_empty(memory_db)
    billing = AssemblyCategoryBillingService()
    billing.ensure_seed_if_empty(memory_db)
    rates = billing.finished_fee_rates(memory_db)
    assert rates.finance_rate == Decimal("0.02")
    assert rates.management_rate == Decimal("0.02")
    assert rates.warehouse_packaging_rate == Decimal("0.01")
    assert rates.scrap_rate == Decimal("0.003")
    assert rates.pretax_profit_rate == Decimal("0.02")

    categories, _category_total = AssemblyCategoryService().list_page(
        memory_db, AssemblyCategoryQuery(page=1, size=20)
    )
    fees, _fee_total = FeeArchiveService().list_page(memory_db, FeeArchiveQuery(page=1, size=20))
    warehouse = next(fee for fee in fees if fee.code == "warehouse_packaging")
    for category in categories:
        billing.replace_selection(
            memory_db,
            category.id,
            CategoryBillingReplace(fee_archive_ids=[warehouse.id]),
            SYSTEM_USER,
        )
    cleared = billing.finished_fee_rates(memory_db)
    assert cleared.finance_rate == Decimal("0")
    assert cleared.scrap_rate == Decimal("0")
    assert cleared.warehouse_packaging_rate == Decimal("0.01")


def test_missing_scrap_fee_is_added_without_changing_rates(memory_db: Session) -> None:
    AssemblyCategoryService().ensure_seed_if_empty(memory_db)
    FeeArchiveService().ensure_seed_if_empty(memory_db)
    memory_db.execute(text("DELETE FROM fee_archives WHERE code = 'scrap'"))
    memory_db.commit()
    fees, _fee_total = FeeArchiveService().list_page(memory_db, FeeArchiveQuery(page=1, size=20))
    financial = next(fee for fee in fees if fee.code == "financial")
    FeeArchiveService().update(
        memory_db,
        financial.id,
        FeeArchiveUpdate(
            name=financial.name,
            charge_basis=financial.charge_basis,
            charge_rate=Decimal("0.05"),
            sort_order=financial.sort_order,
            is_enabled=True,
        ),
        SYSTEM_USER,
    )
    billing = AssemblyCategoryBillingService()
    billing.ensure_seed_if_empty(memory_db)
    added = FeeArchiveService().ensure_missing_seed_fees(memory_db)
    assert added == ("scrap",)
    again, _again_total = FeeArchiveService().list_page(memory_db, FeeArchiveQuery(page=1, size=20))
    kept = next(fee for fee in again if fee.code == "financial")
    assert kept.model_dump()["charge_rate"] == "0.050000"
    billing.check_missing_seed_fees(memory_db, added)
    rates = billing.finished_fee_rates(memory_db)
    assert rates.scrap_rate == Decimal("0.003")
    assert rates.finance_rate == Decimal("0.05")
