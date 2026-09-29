"""钢价政策 Repository。

查询见 queries.py，写入见 writes.py，导出见 export.py，过滤条件见 types.py。
本文件是门面：独立查询/写入类，这里只委托。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.yishiyiyi import SteelPriceLadderItem, SteelPricePolicy
from app.repositories.yishiyiyi.policy.dto import PolicyFilterOptions
from app.repositories.yishiyiyi.policy.export import SteelPricePolicyExport
from app.repositories.yishiyiyi.policy.queries import SteelPricePolicyQueries
from app.repositories.yishiyiyi.policy.types import MatchFilter, PolicyFilter
from app.repositories.yishiyiyi.policy.writes import SteelPricePolicyWrites
from app.schemas.dto.steel_price_policy_dto import (
    LadderItemUpdate,
    PolicyUpdate,
    SteelPriceLadderItemWrite,
    SteelPricePolicyWrite,
)

__all__ = [
    "SteelPricePolicyRepository",
    "MatchFilter",
    "PolicyFilter",
]


class SteelPricePolicyRepository:
    """钢价政策数据访问。"""

    def __init__(self) -> None:
        self._queries = SteelPricePolicyQueries()
        self._writes = SteelPricePolicyWrites(self._queries)
        self._export = SteelPricePolicyExport()

    def get_by_id(
        self,
        db: Session,
        policy_id: int,
        load_items: bool = True,
    ) -> SteelPricePolicy | None:
        return self._queries.get_by_id(db, policy_id, load_items)

    def paginate(
        self,
        db: Session,
        policy_filter: PolicyFilter,
    ) -> tuple[list[SteelPricePolicy], int]:
        return self._queries.paginate(db, policy_filter)

    def count_items(self, db: Session, policy_id: int) -> int:
        return self._queries.count_items(db, policy_id)

    def get_filter_options(self, db: Session) -> PolicyFilterOptions:
        return self._queries.get_filter_options(db)

    def get_distinct_months_for_year(self, db: Session, year: int) -> list[int]:
        return self._queries.get_distinct_months_for_year(db, year)

    def get_policy_id_by_key(
        self,
        db: Session,
        match_filter: MatchFilter,
    ) -> int | None:
        return self._queries.get_policy_id_by_key(db, match_filter)

    def policy_exists_with_key(
        self,
        db: Session,
        match_filter: MatchFilter,
        exclude_id: int | None = None,
    ) -> bool:
        return self._queries.policy_exists_with_key(db, match_filter, exclude_id)

    def find_candidate_policies(
        self,
        db: Session,
        match_filter: MatchFilter,
    ) -> list[SteelPricePolicy]:
        return self._queries.find_candidate_policies(db, match_filter)

    def list_for_period(
        self,
        db: Session,
        *,
        year: int,
        month: int,
    ) -> list[SteelPricePolicy]:
        return self._queries.list_for_period(db, year=year, month=month)

    def get_item_by_id(self, db: Session, item_id: int) -> SteelPriceLadderItem | None:
        return self._queries.get_item_by_id(db, item_id)

    def create_policy(self, db: Session, data: SteelPricePolicyWrite) -> SteelPricePolicy:
        return self._writes.create_policy(db, data)

    def update_policy(
        self,
        db: Session,
        policy_id: int,
        update_data: PolicyUpdate,
        *,
        updated_by: str,
    ) -> SteelPricePolicy | None:
        return self._writes.update_policy(db, policy_id, update_data, updated_by=updated_by)

    def delete_policy(self, db: Session, policy_id: int) -> bool:
        return self._writes.delete_policy(db, policy_id)

    def add_items(
        self,
        db: Session,
        policy_id: int,
        items_data: list[SteelPriceLadderItemWrite],
    ) -> list[SteelPriceLadderItem]:
        return self._writes.add_items(db, policy_id, items_data)

    def update_item(
        self,
        db: Session,
        item_id: int,
        update_data: LadderItemUpdate,
        *,
        updated_by: str,
    ) -> SteelPriceLadderItem | None:
        return self._writes.update_item(db, item_id, update_data, updated_by=updated_by)

    def delete_item(self, db: Session, item_id: int) -> bool:
        return self._writes.delete_item(db, item_id)

    def delete_items_by_policy_id(self, db: Session, policy_id: int) -> int:
        return self._writes.delete_items_by_policy_id(db, policy_id)

    def replace_items(
        self,
        db: Session,
        policy_id: int,
        new_items_data: list[SteelPriceLadderItemWrite],
    ) -> list[SteelPriceLadderItem]:
        return self._writes.replace_items(db, policy_id, new_items_data)

    def count_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
    ) -> int:
        return self._writes.count_by_conditions(
            db, year=year, month=month, steel_mill=steel_mill, steel_mill_id=steel_mill_id
        )

    def delete_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
    ) -> int:
        return self._writes.delete_by_conditions(
            db, year=year, month=month, steel_mill=steel_mill, steel_mill_id=steel_mill_id
        )

    def get_policy_ids_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
    ) -> list[int]:
        return self._writes.get_policy_ids_by_conditions(
            db, year=year, month=month, steel_mill=steel_mill, steel_mill_id=steel_mill_id
        )

    def list_policies_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
        category_names_in: frozenset[str] | None = None,
        category_filter_no_match: bool = False,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[SteelPricePolicy]:
        return self._export.list_policies_for_export(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            steel_mill_id=steel_mill_id,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
            skip=skip,
            limit=limit,
        )

    def list_export_pairs(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
        category_names_in: frozenset[str] | None = None,
        category_filter_no_match: bool = False,
        skip: int = 0,
        limit: int | None = None,
    ) -> list[tuple[SteelPricePolicy, SteelPriceLadderItem | None]]:
        return self._export.list_export_pairs(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            steel_mill_id=steel_mill_id,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
            skip=skip,
            limit=limit,
        )

    def list_items_for_export(
        self,
        db: Session,
        policy_ids: list[int],
    ) -> list[SteelPriceLadderItem]:
        return self._export.list_items_for_export(db, policy_ids)

    def count_policies_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
        category_names_in: frozenset[str] | None = None,
        category_filter_no_match: bool = False,
    ) -> int:
        return self._export.count_policies_for_export(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            steel_mill_id=steel_mill_id,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
        )

    def count_export_rows(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
        category_names_in: frozenset[str] | None = None,
        category_filter_no_match: bool = False,
    ) -> int:
        return self._export.count_export_rows(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            steel_mill_id=steel_mill_id,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
        )

    def count_items_for_export(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
        category_names_in: frozenset[str] | None = None,
        category_filter_no_match: bool = False,
        policy_type: str | None = None,
    ) -> int:
        return self._export.count_items_for_export(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
            steel_mill_id=steel_mill_id,
            category_names_in=category_names_in,
            category_filter_no_match=category_filter_no_match,
            policy_type=policy_type,
        )
