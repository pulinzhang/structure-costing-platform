"""钢价政策列表与匹配查询。"""

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.common.steel_grade_category import CANONICAL_CATEGORY_NAMES
from app.models.yishiyiyi import SteelPriceLadderItem, SteelPricePolicy
from app.repositories.yishiyiyi.policy.dto import PolicyFilterOptions
from app.repositories.yishiyiyi.policy.filters import (
    apply_category_scope,
    apply_optional_policy_filters,
    distinct_values,
)
from app.repositories.yishiyiyi.policy.types import MatchFilter, PolicyFilter


class SteelPricePolicyQueries:
    """主表查询、筛选下拉、业务键匹配。"""

    def get_by_id(
        self,
        db: Session,
        policy_id: int,
        load_items: bool = True,
    ) -> SteelPricePolicy | None:
        """
        根据主键查询政策。

        Args:
            db: 数据库会话
            policy_id: 政策主键
            load_items: 是否预加载明细，默认 True
        """
        query = db.query(SteelPricePolicy)
        if load_items:
            query = query.options(joinedload(SteelPricePolicy.items))
        return query.filter(SteelPricePolicy.id == policy_id).first()

    def paginate(
        self,
        db: Session,
        policy_filter: PolicyFilter,
    ) -> tuple[list[SteelPricePolicy], int]:
        """
        分页筛选政策主表。

        Args:
            db: 数据库会话
            policy_filter: 过滤条件（包含分页参数）

        Returns:
            (records, total) 元组
        """
        query = db.query(SteelPricePolicy)

        if policy_filter.year is not None:
            query = query.filter(SteelPricePolicy.year == policy_filter.year)
        if policy_filter.month is not None:
            query = query.filter(SteelPricePolicy.month == policy_filter.month)
        if policy_filter.steel_mill_id is not None:
            query = query.filter(SteelPricePolicy.steel_mill_id == policy_filter.steel_mill_id)
        elif policy_filter.steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == policy_filter.steel_mill)
        query = apply_category_scope(
            query,
            category_names_in=policy_filter.category_names_in,
            category_filter_no_match=policy_filter.category_filter_no_match,
        )
        if policy_filter.policy_type:
            query = query.filter(SteelPricePolicy.policy_type == policy_filter.policy_type)
        if policy_filter.grade_type:
            query = query.filter(SteelPricePolicy.grade_type == policy_filter.grade_type)

        total = query.count()
        records = (
            query.order_by(
                SteelPricePolicy.year.asc(),
                SteelPricePolicy.month.asc(),
                SteelPricePolicy.id.asc(),
                SteelPricePolicy.steel_mill,
                SteelPricePolicy.category_name,
                SteelPricePolicy.policy_type,
                SteelPricePolicy.grade_type,
                SteelPricePolicy.grade_value,
            )
            .offset(policy_filter.skip)
            .limit(policy_filter.limit)
            .all()
        )
        return records, total

    def count_items(self, db: Session, policy_id: int) -> int:
        """返回指定政策下的明细条数。"""
        return (
            db.query(func.count(SteelPriceLadderItem.id))
            .filter(SteelPriceLadderItem.policy_id == policy_id)
            .scalar()
            or 0
        )

    def get_filter_options(self, db: Session) -> PolicyFilterOptions:
        """返回各字段的筛选下拉选项。"""
        years = sorted(
            distinct_values(db, SteelPricePolicy.year, descending=True),
            reverse=True,
        )
        months = distinct_values(db, SteelPricePolicy.month)
        category_names = list(CANONICAL_CATEGORY_NAMES)
        policy_types = distinct_values(db, SteelPricePolicy.policy_type)
        grade_types = [
            value
            for value in distinct_values(db, SteelPricePolicy.grade_type, filter_none=True)
            if value is not None
        ]
        grade_values = [
            value
            for value in distinct_values(db, SteelPricePolicy.grade_value, filter_none=True)
            if value is not None
        ]
        return PolicyFilterOptions(
            years=years,
            months=months,
            category_names=category_names,
            policy_types=policy_types,
            grade_types=grade_types,
            grade_values=grade_values,
        )

    def get_distinct_months_for_year(self, db: Session, year: int) -> list[int]:
        results = (
            db.query(SteelPricePolicy.month)
            .filter(SteelPricePolicy.year == year)
            .distinct()
            .order_by(SteelPricePolicy.month)
            .all()
        )
        return [int(r[0]) for r in results if r[0] is not None]

    def get_policy_id_by_key(
        self,
        db: Session,
        match_filter: MatchFilter,
    ) -> int | None:
        """
        根据业务键查询政策 ID（用于 upsert 场景获取旧记录 ID）。

        Args:
            db: 数据库会话
            match_filter: 匹配过滤条件
        """
        query = apply_optional_policy_filters(
            db.query(SteelPricePolicy.id).filter(
                SteelPricePolicy.year == match_filter.year,
                SteelPricePolicy.month == match_filter.month,
                SteelPricePolicy.steel_mill_id == match_filter.steel_mill_id
                if match_filter.steel_mill_id is not None
                else SteelPricePolicy.steel_mill == match_filter.steel_mill,
                SteelPricePolicy.category_name == match_filter.category_name,
                SteelPricePolicy.policy_type == match_filter.policy_type,
            ),
            grade_type=match_filter.grade_type,
            grade_value=match_filter.grade_value,
            base_thickness=match_filter.base_thickness,
        )
        result = query.first()
        return result[0] if result else None

    def policy_exists_with_key(
        self,
        db: Session,
        match_filter: MatchFilter,
        exclude_id: int | None = None,
    ) -> bool:
        """
        检查指定业务键是否已存在（用于应用层唯一冲突检查）。

        Args:
            db: 数据库会话
            match_filter: 匹配过滤条件
            exclude_id: 排除的记录 ID（用于更新时排除自身）
        """
        policy_id = self.get_policy_id_by_key(db, match_filter)
        return not (policy_id is None or (exclude_id is not None and policy_id == exclude_id))

    def find_candidate_policies(
        self,
        db: Session,
        match_filter: MatchFilter,
    ) -> list[SteelPricePolicy]:
        """
        根据政策维度条件查找候选政策（含明细）。

        Args:
            db: 数据库会话
            match_filter: 匹配过滤条件
        """
        query = (
            db.query(SteelPricePolicy)
            .options(joinedload(SteelPricePolicy.items))
            .filter(
                SteelPricePolicy.year == match_filter.year,
                SteelPricePolicy.month == match_filter.month,
                SteelPricePolicy.steel_mill_id == match_filter.steel_mill_id
                if match_filter.steel_mill_id is not None
                else SteelPricePolicy.steel_mill == match_filter.steel_mill,
                SteelPricePolicy.category_name == match_filter.category_name,
                SteelPricePolicy.policy_type == match_filter.policy_type,
            )
        )
        query = apply_optional_policy_filters(
            query,
            grade_type=match_filter.grade_type,
            grade_value=match_filter.grade_value,
            base_thickness=match_filter.base_thickness,
        )
        return query.all()

    def list_for_period(
        self,
        db: Session,
        *,
        year: int,
        month: int,
    ) -> list[SteelPricePolicy]:
        """按年月一次加载全部政策（含阶梯明细），供计算编排内存匹配。"""
        return (
            db.query(SteelPricePolicy)
            .options(joinedload(SteelPricePolicy.items))
            .filter(
                SteelPricePolicy.year == year,
                SteelPricePolicy.month == month,
            )
            .order_by(SteelPricePolicy.id.asc())
            .all()
        )

    def get_item_by_id(self, db: Session, item_id: int) -> SteelPriceLadderItem | None:
        """按明细 ID 查询。"""
        return db.query(SteelPriceLadderItem).filter(SteelPriceLadderItem.id == item_id).first()
