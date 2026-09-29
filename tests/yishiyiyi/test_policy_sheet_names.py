"""加减价政策表页下拉：按年度、月份、钢厂去重。"""

from app.models.yishiyiyi import SteelPricePolicy
from app.repositories.yishiyiyi.policy.steel_price_policy_repository import (
    SteelPricePolicyRepository,
)
from app.services.yishiyiyi.policy.export.service import SteelPricePolicyExportService


def test_distinct_sheet_names_are_unique(db_session):
    names = SteelPricePolicyRepository().list_distinct_sheet_names(db_session)
    assert names == sorted(set(names))
    assert all(name.strip() for name in names)


def test_unknown_year_has_no_sheet_names(db_session):
    names = SteelPricePolicyRepository().list_distinct_sheet_names(db_session, year=2099)
    assert names == []


def test_unknown_sheet_export_count_is_zero(db_session):
    count = SteelPricePolicyExportService().count_export_data(
        db_session,
        sheet_name="__no_such_sheet__",
    )
    assert count == 0


def test_sheet_names_narrow_by_year_and_mill(db_session):
    repo = SteelPricePolicyRepository()
    all_names = repo.list_distinct_sheet_names(db_session)
    row = (
        db_session.query(SteelPricePolicy.year, SteelPricePolicy.steel_mill_id)
        .filter(SteelPricePolicy.sheet_name.isnot(None), SteelPricePolicy.sheet_name != "")
        .first()
    )
    if row is None:
        return
    year, steel_mill_id = row
    scoped = repo.list_distinct_sheet_names(
        db_session,
        year=year,
        steel_mill_id=steel_mill_id,
    )
    assert scoped
    assert set(scoped).issubset(set(all_names))
    missing = SteelPricePolicyExportService().list_sheet_names(
        db_session,
        year=year,
        steel_mill="__missing_mill__",
    )
    assert missing == []
