"""
钢价政策 Repository
只负责数据库访问，事务由 Service 层管理
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session, joinedload

from app.models.steel_price_policy import SteelPricePolicy, SteelPriceLadderItem
from app.repositories.steel_price_policy.dto import ExportRow, FilterOptions


class PolicyFilter:
    """政策查询过滤条件（封装分页参数）。"""

    def __init__(
        self,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
        category_name: Optional[str] = None,
        policy_type: Optional[str] = None,
        grade_type: Optional[str] = None,
        grade_value: Optional[str] = None,
        skip: int = 0,
        limit: int = 20,
    ):
        self.year = year
        self.month = month
        self.steel_mill = steel_mill
        self.category_name = category_name
        self.policy_type = policy_type
        self.grade_type = grade_type
        self.grade_value = grade_value
        self.skip = skip
        self.limit = limit


class MatchFilter:
    """阶梯匹配查询过滤条件。"""

    def __init__(
        self,
        *,
        year: int,
        month: int,
        steel_mill: str,
        category_name: str,
        policy_type: str,
        grade_type: Optional[str] = None,
        grade_value: Optional[str] = None,
        base_thickness: Optional[Decimal] = None,
    ):
        self.year = year
        self.month = month
        self.steel_mill = steel_mill
        self.category_name = category_name
        self.policy_type = policy_type
        self.grade_type = grade_type
        self.grade_value = grade_value
        self.base_thickness = base_thickness


class SteelPricePolicyRepository:
    """钢价政策数据访问。"""

    # ---- 主表查询 ----

    def get_by_id(
        self,
        db: Session,
        policy_id: int,
        load_items: bool = True,
    ) -> Optional[SteelPricePolicy]:
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
        if policy_filter.steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == policy_filter.steel_mill)
        if policy_filter.category_name:
            query = query.filter(SteelPricePolicy.category_name == policy_filter.category_name)
        if policy_filter.policy_type:
            query = query.filter(SteelPricePolicy.policy_type == policy_filter.policy_type)
        if policy_filter.grade_type:
            query = query.filter(SteelPricePolicy.grade_type == policy_filter.grade_type)
        if policy_filter.grade_value:
            query = query.filter(SteelPricePolicy.grade_value.contains(policy_filter.grade_value))

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

    # ---- 筛选选项 ----

    def _distinct_values(
        self,
        db: Session,
        column,
        *,
        filter_none: bool = False,
        descending: bool = False,
    ) -> list:
        """通用 distinct 值查询。"""
        query = db.query(distinct(column))
        if filter_none:
            query = query.filter(column.isnot(None))
        order_col = column.desc() if descending else column.asc()
        return [r[0] for r in query.order_by(order_col).all()]

    def get_filter_options(self, db: Session) -> FilterOptions:
        """返回各字段的筛选下拉选项。"""
        years = sorted(
            self._distinct_values(db, SteelPricePolicy.year, descending=True),
            reverse=True,
        )
        months = self._distinct_values(db, SteelPricePolicy.month)
        steel_mills = self._distinct_values(db, SteelPricePolicy.steel_mill)
        category_names = self._distinct_values(db, SteelPricePolicy.category_name)
        policy_types = self._distinct_values(db, SteelPricePolicy.policy_type)
        grade_types = self._distinct_values(db, SteelPricePolicy.grade_type, filter_none=True)
        grade_values = self._distinct_values(db, SteelPricePolicy.grade_value, filter_none=True)
        return FilterOptions(
            years=years,
            months=months,
            steel_mills=steel_mills,
            category_names=category_names,
            policy_types=policy_types,
            grade_types=grade_types,
            grade_values=grade_values,
        )

    # ---- 主表写操作 ----

    def create_policy(self, db: Session, data: dict) -> SteelPricePolicy:
        """
        创建政策主表记录（不含明细）。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        policy = SteelPricePolicy(**data)
        db.add(policy)
        return policy

    def update_policy(
        self,
        db: Session,
        policy_id: int,
        update_data: dict,
    ) -> Optional[SteelPricePolicy]:
        """
        按主键更新政策主表字段，返回更新后记录或 None（不存在）。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        policy = self.get_by_id(db, policy_id, load_items=False)
        if policy is None:
            return None
        for column, value in update_data.items():
            if hasattr(policy, column):
                setattr(policy, column, value)
        return policy

    def delete_policy(self, db: Session, policy_id: int) -> bool:
        """
        按主键删除政策（含级联明细）。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        policy = self.get_by_id(db, policy_id, load_items=False)
        if policy is None:
            return False
        db.delete(policy)
        return True

    def _apply_optional_policy_filters(
        self,
        query,
        *,
        grade_type: Optional[str] = None,
        grade_value: Optional[str] = None,
        base_thickness: Optional[Decimal] = None,
    ):
        """对 policy 的可选过滤字段应用条件（支持 NULL 精确匹配）。"""
        if grade_type is not None:
            query = query.filter(SteelPricePolicy.grade_type == grade_type)
        else:
            query = query.filter(SteelPricePolicy.grade_type.is_(None))

        if grade_value is not None:
            query = query.filter(SteelPricePolicy.grade_value == grade_value)
        else:
            query = query.filter(SteelPricePolicy.grade_value.is_(None))

        if base_thickness is not None:
            query = query.filter(SteelPricePolicy.base_thickness == base_thickness)
        else:
            query = query.filter(SteelPricePolicy.base_thickness.is_(None))

        return query

    def get_policy_id_by_key(
        self,
        db: Session,
        match_filter: MatchFilter,
    ) -> Optional[int]:
        """
        根据业务键查询政策 ID（用于 upsert 场景获取旧记录 ID）。

        Args:
            db: 数据库会话
            match_filter: 匹配过滤条件
        """
        query = db.query(SteelPricePolicy.id).filter(
            SteelPricePolicy.year == match_filter.year,
            SteelPricePolicy.month == match_filter.month,
            SteelPricePolicy.steel_mill == match_filter.steel_mill,
            SteelPricePolicy.category_name == match_filter.category_name,
            SteelPricePolicy.policy_type == match_filter.policy_type,
        )
        query = self._apply_optional_policy_filters(
            query,
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
        exclude_id: Optional[int] = None,
    ) -> bool:
        """
        检查指定业务键是否已存在（用于应用层唯一冲突检查）。

        Args:
            db: 数据库会话
            match_filter: 匹配过滤条件
            exclude_id: 排除的记录 ID（用于更新时排除自身）
        """
        policy_id = self.get_policy_id_by_key(db, match_filter)
        if policy_id is None:
            return False
        if exclude_id is not None and policy_id == exclude_id:
            return False
        return True

    # ---- 明细写操作 ----

    def add_items(
        self,
        db: Session,
        policy_id: int,
        items_data: list[dict],
    ) -> list[SteelPriceLadderItem]:
        """
        批量新增明细。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        created = []
        for item_data in items_data:
            item = SteelPriceLadderItem(policy_id=policy_id, **item_data)
            db.add(item)
            created.append(item)
        return created

    def update_item(
        self,
        db: Session,
        item_id: int,
        update_data: dict,
    ) -> Optional[SteelPriceLadderItem]:
        """
        更新单条明细。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        item = db.query(SteelPriceLadderItem).filter(SteelPriceLadderItem.id == item_id).first()
        if item is None:
            return None
        for column, value in update_data.items():
            if hasattr(item, column):
                setattr(item, column, value)
        return item

    def delete_item(self, db: Session, item_id: int) -> bool:
        """
        删除单条明细。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        item = db.query(SteelPriceLadderItem).filter(SteelPriceLadderItem.id == item_id).first()
        if item is None:
            return False
        db.delete(item)
        return True

    def delete_items_by_policy_id(self, db: Session, policy_id: int) -> int:
        """
        删除指定政策下的全部明细。
        注意：此方法不 flush，由调用方（Service）控制事务。
        返回被删除的明细数量。
        """
        count = (
            db.query(SteelPriceLadderItem)
            .filter(SteelPriceLadderItem.policy_id == policy_id)
            .delete(synchronize_session=False)
        )
        return count

    def replace_items(
        self,
        db: Session,
        policy_id: int,
        new_items_data: list[dict],
    ) -> list[SteelPriceLadderItem]:
        """
        整组替换政策下的全部明细（旧明细级联删除）。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        self.delete_items_by_policy_id(db, policy_id)
        return self.add_items(db, policy_id, new_items_data)

    def get_item_by_id(self, db: Session, item_id: int) -> Optional[SteelPriceLadderItem]:
        """按明细 ID 查询。"""
        return db.query(SteelPriceLadderItem).filter(SteelPriceLadderItem.id == item_id).first()

    # ---- 阶梯匹配查询 ----

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
                SteelPricePolicy.steel_mill == match_filter.steel_mill,
                SteelPricePolicy.category_name == match_filter.category_name,
                SteelPricePolicy.policy_type == match_filter.policy_type,
            )
        )
        query = self._apply_optional_policy_filters(
            query,
            grade_type=match_filter.grade_type,
            grade_value=match_filter.grade_value,
            base_thickness=match_filter.base_thickness,
        )
        return query.all()

    # ---- 导出查询（原 get_export_data 相关方法已移至 ExportService）----

    def list_policies_for_export(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> list[SteelPricePolicy]:
        """
        获取导出所需的主表数据（供 ExportService 调用）。

        Returns:
            政策主表列表（按年份、月份、ID 排序）
        """
        query = db.query(SteelPricePolicy)

        if year is not None:
            query = query.filter(SteelPricePolicy.year == year)
        if month is not None:
            query = query.filter(SteelPricePolicy.month == month)
        if steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == steel_mill)

        query = query.order_by(
            SteelPricePolicy.year.asc(),
            SteelPricePolicy.month.asc(),
            SteelPricePolicy.id.asc(),
            SteelPricePolicy.steel_mill,
        )

        if skip:
            query = query.offset(skip)
        if limit:
            query = query.limit(limit)

        return query.all()

    def list_items_for_export(
        self,
        db: Session,
        policy_ids: list[int],
    ) -> list[SteelPriceLadderItem]:
        """
        根据政策 ID 列表获取明细数据（供 ExportService 调用）。

        Returns:
            明细列表（按 policy_id、sort_order、id 排序）
        """
        if not policy_ids:
            return []

        return (
            db.query(SteelPriceLadderItem)
            .filter(SteelPriceLadderItem.policy_id.in_(policy_ids))
            .order_by(
                SteelPriceLadderItem.policy_id,
                SteelPriceLadderItem.sort_order,
                SteelPriceLadderItem.id,
            )
            .all()
        )

    def count_policies_for_export(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> int:
        """统计主表记录数（供 ExportService 调用）。"""
        query = db.query(func.count(SteelPricePolicy.id))

        if year is not None:
            query = query.filter(SteelPricePolicy.year == year)
        if month is not None:
            query = query.filter(SteelPricePolicy.month == month)
        if steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == steel_mill)

        return query.scalar() or 0

    def count_items_for_export(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
        policy_type: Optional[str] = None,
    ) -> int:
        """
        统计明细总数（供 ExportService / 统计接口调用）。
        通过 JOIN 主表并应用相同的过滤条件来确保一致性。
        """
        query = db.query(func.count(SteelPriceLadderItem.id)).join(
            SteelPricePolicy,
            SteelPricePolicy.id == SteelPriceLadderItem.policy_id,
        )

        if year is not None:
            query = query.filter(SteelPricePolicy.year == year)
        if month is not None:
            query = query.filter(SteelPricePolicy.month == month)
        if steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == steel_mill)
        if policy_type:
            query = query.filter(SteelPricePolicy.policy_type == policy_type)

        return query.scalar() or 0

    # ---- 条件批量删除 ----

    def count_by_conditions(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> int:
        """
        根据条件统计政策数量（删除前查询）。

        Returns:
            符合条件的政策数量
        """
        query = db.query(func.count(SteelPricePolicy.id))

        if year is not None:
            query = query.filter(SteelPricePolicy.year == year)
        if month is not None:
            query = query.filter(SteelPricePolicy.month == month)
        if steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == steel_mill)

        return query.scalar() or 0

    def delete_by_conditions(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> int:
        """
        根据条件批量删除政策。
        注意：此方法不 flush，由调用方（Service）控制事务。
        返回待删除的政策数量。
        级联删除依赖数据库外键的 CASCADE 配置。
        """
        count = self.count_by_conditions(
            db,
            year=year,
            month=month,
            steel_mill=steel_mill,
        )
        query = db.query(SteelPricePolicy)

        if year is not None:
            query = query.filter(SteelPricePolicy.year == year)
        if month is not None:
            query = query.filter(SteelPricePolicy.month == month)
        if steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == steel_mill)

        query.delete(synchronize_session=False)
        return count

    def get_policy_ids_by_conditions(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> list[int]:
        """
        根据条件获取政策 ID 列表（用于级联删除前的预处理）。
        """
        query = db.query(SteelPricePolicy.id)

        if year is not None:
            query = query.filter(SteelPricePolicy.year == year)
        if month is not None:
            query = query.filter(SteelPricePolicy.month == month)
        if steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == steel_mill)

        return [row[0] for row in query.all()]
