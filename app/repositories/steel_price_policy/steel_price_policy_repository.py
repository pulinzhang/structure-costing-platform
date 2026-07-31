"""
钢价政策 Repository
只负责数据库访问，事务由 Service 层管理
"""

import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session, joinedload

from app.models.steel_price_policy import SteelPricePolicy, SteelPriceLadderItem
from app.repositories.steel_price_policy.dto import ExportRow, FilterOptions


logger = logging.getLogger("repository.steel_price_policy")


class SteelPricePolicyRepository:
    """钢价政策数据访问。"""

    # ---- 主表查询 ----

    def get_by_id(self, db: Session, policy_id: int) -> Optional[SteelPricePolicy]:
        """根据主键查询政策（预加载全部明细）。"""
        return (
            db.query(SteelPricePolicy)
            .options(joinedload(SteelPricePolicy.items))
            .filter(SteelPricePolicy.id == policy_id)
            .first()
        )

    def get_by_id_unsafe(self, db: Session, policy_id: int) -> Optional[SteelPricePolicy]:
        """根据主键查询政策，不预加载明细（用于删除等不需要明细的场景）。"""
        return db.query(SteelPricePolicy).filter(SteelPricePolicy.id == policy_id).first()

    def paginate(
        self,
        db: Session,
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
    ) -> tuple[list[SteelPricePolicy], int]:
        """分页筛选政策主表，附加子表行数聚合。"""
        query = db.query(SteelPricePolicy)

        if year is not None:
            query = query.filter(SteelPricePolicy.year == year)
        if month is not None:
            query = query.filter(SteelPricePolicy.month == month)
        if steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == steel_mill)
        if category_name:
            query = query.filter(SteelPricePolicy.category_name == category_name)
        if policy_type:
            query = query.filter(SteelPricePolicy.policy_type == policy_type)
        if grade_type:
            query = query.filter(SteelPricePolicy.grade_type == grade_type)
        if grade_value:
            query = query.filter(SteelPricePolicy.grade_value.contains(grade_value))

        total = query.count()
        records = (
            query.order_by(
                SteelPricePolicy.year.desc(),
                SteelPricePolicy.month.desc(),
                SteelPricePolicy.steel_mill,
                SteelPricePolicy.category_name,
                SteelPricePolicy.policy_type,
                SteelPricePolicy.grade_type,
                SteelPricePolicy.grade_value,
            )
            .offset(skip)
            .limit(limit)
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

    def get_filter_options(self, db: Session) -> FilterOptions:
        """返回各字段的筛选下拉选项。"""
        years = sorted(
            [r[0] for r in db.query(distinct(SteelPricePolicy.year)).order_by(SteelPricePolicy.year.desc()).all()],
            reverse=True,
        )
        months = [
            r[0] for r in
            db.query(distinct(SteelPricePolicy.month)).order_by(SteelPricePolicy.month).all()
        ]
        steel_mills = [
            r[0] for r in
            db.query(distinct(SteelPricePolicy.steel_mill)).order_by(SteelPricePolicy.steel_mill).all()
        ]
        category_names = [
            r[0] for r in
            db.query(distinct(SteelPricePolicy.category_name)).order_by(SteelPricePolicy.category_name).all()
        ]
        policy_types = [
            r[0] for r in
            db.query(distinct(SteelPricePolicy.policy_type)).order_by(SteelPricePolicy.policy_type).all()
        ]
        grade_types = [
            r[0] for r in
            db.query(distinct(SteelPricePolicy.grade_type)).filter(
                SteelPricePolicy.grade_type.isnot(None)
            ).order_by(SteelPricePolicy.grade_type).all()
        ]
        grade_values = [
            r[0] for r in
            db.query(distinct(SteelPricePolicy.grade_value)).filter(
                SteelPricePolicy.grade_value.isnot(None)
            ).order_by(SteelPricePolicy.grade_value).all()
        ]
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

    def create_policy(self, db: Session, data: dict[str, Any]) -> SteelPricePolicy:
        """创建政策主表记录（不含明细），由 Service 管理 flush/commit。"""
        policy = SteelPricePolicy(**data)
        db.add(policy)
        db.flush()
        base_t_str = f"{data.get('base_thickness'):.2f}" if data.get("base_thickness") is not None else "N/A"
        logger.info(
            "创建钢价政策: year=%s month=%s steel_mill=%s category=%s type=%s grade_type=%s grade_value=%s base_t=%s id=%s",
            data.get("year"),
            data.get("month"),
            data.get("steel_mill"),
            data.get("category_name"),
            data.get("policy_type"),
            data.get("grade_type"),
            data.get("grade_value"),
            base_t_str,
            policy.id,
        )
        return policy

    def update_policy(
        self,
        db: Session,
        policy_id: int,
        update_data: dict[str, Any],
    ) -> Optional[SteelPricePolicy]:
        """按主键更新政策主表字段，返回更新后记录或 None（不存在）。"""
        policy = self.get_by_id_unsafe(db, policy_id)
        if policy is None:
            return None
        for column, value in update_data.items():
            if hasattr(policy, column):
                setattr(policy, column, value)
        db.flush()
        logger.info("更新钢价政策: id=%s", policy_id)
        return policy

    def delete_policy(self, db: Session, policy_id: int) -> bool:
        """按主键删除政策（含级联明细）。"""
        policy = self.get_by_id_unsafe(db, policy_id)
        if policy is None:
            return False
        db.delete(policy)
        db.flush()
        logger.info("删除钢价政策: id=%s", policy_id)
        return True

    def policy_exists_with_key(
        self,
        db: Session,
        year: int,
        month: int,
        steel_mill: str,
        category_name: str,
        policy_type: str,
        grade_type: Optional[str],
        grade_value: Optional[str],
        base_thickness: Optional[Any],
        exclude_id: Optional[int] = None,
    ) -> bool:
        """检查指定业务键是否已存在（用于应用层唯一冲突检查）。"""
        query = db.query(SteelPricePolicy).filter(
            SteelPricePolicy.year == year,
            SteelPricePolicy.month == month,
            SteelPricePolicy.steel_mill == steel_mill,
            SteelPricePolicy.category_name == category_name,
            SteelPricePolicy.policy_type == policy_type,
        )
        # grade_type / grade_value / base_thickness 允许 NULL，需要用 or_ 覆盖两侧
        from sqlalchemy import or_
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

        if exclude_id is not None:
            query = query.filter(SteelPricePolicy.id != exclude_id)

        return query.first() is not None

    # ---- 明细写操作 ----

    def add_items(self, db: Session, policy_id: int, items_data: list[dict[str, Any]]) -> list[SteelPriceLadderItem]:
        """批量新增明细。"""
        created = []
        for item_data in items_data:
            item = SteelPriceLadderItem(policy_id=policy_id, **item_data)
            db.add(item)
            created.append(item)
        db.flush()
        return created

    def update_item(
        self,
        db: Session,
        item_id: int,
        update_data: dict[str, Any],
    ) -> Optional[SteelPriceLadderItem]:
        """更新单条明细。"""
        item = db.query(SteelPriceLadderItem).filter(SteelPriceLadderItem.id == item_id).first()
        if item is None:
            return None
        for column, value in update_data.items():
            if hasattr(item, column):
                setattr(item, column, value)
        db.flush()
        logger.info("更新阶梯明细: id=%s", item_id)
        return item

    def delete_item(self, db: Session, item_id: int) -> bool:
        """删除单条明细。"""
        item = db.query(SteelPriceLadderItem).filter(SteelPriceLadderItem.id == item_id).first()
        if item is None:
            return False
        db.delete(item)
        db.flush()
        logger.info("删除阶梯明细: id=%s", item_id)
        return True

    def replace_items(self, db: Session, policy_id: int, new_items_data: list[dict[str, Any]]) -> list[SteelPriceLadderItem]:
        """整组替换政策下的全部明细（旧明细级联删除）。"""
        db.query(SteelPriceLadderItem).filter(
            SteelPriceLadderItem.policy_id == policy_id
        ).delete(synchronize_session=False)
        db.flush()
        return self.add_items(db, policy_id, new_items_data)

    def get_item_by_id(self, db: Session, item_id: int) -> Optional[SteelPriceLadderItem]:
        """按明细 ID 查询。"""
        return db.query(SteelPriceLadderItem).filter(SteelPriceLadderItem.id == item_id).first()

    # ---- 阶梯匹配查询 ----

    def find_candidate_policies(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        steel_mill: str,
        category_name: str,
        policy_type: str,
        grade_type: Optional[str] = None,
        grade_value: Optional[str] = None,
        base_thickness: Optional[Any] = None,
    ) -> list[SteelPricePolicy]:
        """根据政策维度条件查找候选政策（含明细）。"""
        query = (
            db.query(SteelPricePolicy)
            .options(joinedload(SteelPricePolicy.items))
            .filter(
                SteelPricePolicy.year == year,
                SteelPricePolicy.month == month,
                SteelPricePolicy.steel_mill == steel_mill,
                SteelPricePolicy.category_name == category_name,
                SteelPricePolicy.policy_type == policy_type,
            )
        )

        from sqlalchemy import or_
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

        return query.all()

    # ---- Excel 导出查询 ----

    def get_export_data(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
        skip: int = 0,
        limit: Optional[int] = None,
    ) -> list[ExportRow]:
        """
        获取导出数据（主子表 INNER JOIN 联合查询）
        返回 ExportRow 列表，每行代表一个政策主表+阶梯明细组合
        """
        # 先查询主表
        policy_query = db.query(SteelPricePolicy)

        if year is not None:
            policy_query = policy_query.filter(SteelPricePolicy.year == year)
        if month is not None:
            policy_query = policy_query.filter(SteelPricePolicy.month == month)
        if steel_mill:
            policy_query = policy_query.filter(SteelPricePolicy.steel_mill == steel_mill)

        policy_query = policy_query.order_by(
            SteelPricePolicy.year.desc(),
            SteelPricePolicy.month.desc(),
            SteelPricePolicy.steel_mill,
            SteelPricePolicy.id,
        )

        if skip:
            policy_query = policy_query.offset(skip)
        if limit:
            policy_query = policy_query.limit(limit)

        policies = policy_query.all()

        # 收集所有 policy_id
        policy_ids = [p.id for p in policies]
        if not policy_ids:
            return []

        # 查询对应的阶梯明细
        items_query = db.query(SteelPriceLadderItem).filter(
            SteelPriceLadderItem.policy_id.in_(policy_ids)
        ).order_by(
            SteelPriceLadderItem.policy_id,
            SteelPriceLadderItem.sort_order,
            SteelPriceLadderItem.id,
        )

        items = items_query.all()

        # 按 policy_id 分组
        items_by_policy = {}
        for item in items:
            if item.policy_id not in items_by_policy:
                items_by_policy[item.policy_id] = []
            items_by_policy[item.policy_id].append(item)

        # 构建结果
        results = []
        for policy in policies:
            policy_items = items_by_policy.get(policy.id, [])
            if not policy_items:
                # 没有明细的政策也保留一行
                results.append(self._policy_to_export_row(policy, None))
            for item in policy_items:
                results.append(self._policy_to_export_row(policy, item))

        return results

    def _policy_to_export_row(
        self,
        policy: SteelPricePolicy,
        item: Optional[SteelPriceLadderItem],
    ) -> ExportRow:
        """将政策主表和明细转换为 ExportRow 对象"""
        def to_str(value):
            if value is None:
                return None
            if isinstance(value, Decimal):
                return str(value)
            return value

        return ExportRow(
            policy_id=policy.id,
            year=policy.year,
            month=policy.month,
            steel_mill=policy.steel_mill,
            category_name=policy.category_name,
            policy_type=policy.policy_type,
            grade_type=policy.grade_type,
            grade_value=policy.grade_value,
            base_thickness=to_str(policy.base_thickness),
            item_id=item.id if item else None,
            target_sub_group=item.target_sub_group if item else None,
            thick_min=to_str(item.thick_min) if item else None,
            thick_min_operator=item.thick_min_operator if item else None,
            thick_max=to_str(item.thick_max) if item else None,
            thick_max_operator=item.thick_max_operator if item else None,
            width_min=to_str(item.width_min) if item else None,
            width_min_operator=item.width_min_operator if item else None,
            width_max=to_str(item.width_max) if item else None,
            width_max_operator=item.width_max_operator if item else None,
            price_adjustment=item.price_adjustment if item else None,
            is_base=item.is_base if item else None,
            sort_order=item.sort_order if item else None,
        )

    def count_export_data(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> int:
        """
        统计导出数据总数（主表+明细的行数）
        """
        # 统计有明细的政策数
        policy_query = db.query(SteelPricePolicy).join(
            SteelPriceLadderItem,
            SteelPricePolicy.id == SteelPriceLadderItem.policy_id,
        )

        if year is not None:
            policy_query = policy_query.filter(SteelPricePolicy.year == year)
        if month is not None:
            policy_query = policy_query.filter(SteelPricePolicy.month == month)
        if steel_mill:
            policy_query = policy_query.filter(SteelPricePolicy.steel_mill == steel_mill)

        # 去重统计政策数
        policy_count = (
            policy_query.with_entities(SteelPricePolicy.id)
            .distinct()
            .count()
        )

        # 统计明细总数
        item_query = db.query(SteelPriceLadderItem.id).join(
            SteelPricePolicy,
            SteelPricePolicy.id == SteelPriceLadderItem.policy_id,
        )

        if year is not None:
            item_query = item_query.filter(SteelPricePolicy.year == year)
        if month is not None:
            item_query = item_query.filter(SteelPricePolicy.month == month)
        if steel_mill:
            item_query = item_query.filter(SteelPricePolicy.steel_mill == steel_mill)

        item_count = item_query.count()

        # 总数 = 政策数（有明细的政策）+ 明细数
        return policy_count + item_count

    # ---- 条件批量删除 ----

    def delete_by_conditions(
        self,
        db: Session,
        *,
        year: Optional[int] = None,
        month: Optional[int] = None,
        steel_mill: Optional[str] = None,
    ) -> int:
        """
        根据条件批量删除政策（含级联删除明细）。
        返回删除的政策数量。
        """
        query = db.query(SteelPricePolicy)

        if year is not None:
            query = query.filter(SteelPricePolicy.year == year)
        if month is not None:
            query = query.filter(SteelPricePolicy.month == month)
        if steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == steel_mill)

        count = query.count()
        query.delete(synchronize_session=False)
        db.flush()
        logger.info(
            "批量删除钢价政策: year=%s month=%s steel_mill=%s count=%s",
            year, month, steel_mill, count,
        )
        return count
