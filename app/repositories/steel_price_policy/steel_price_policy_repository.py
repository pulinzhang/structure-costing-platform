"""
钢价政策 Repository
只负责数据库访问，事务由 Service 层管理
"""

import logging
from typing import Any, Optional

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session, joinedload

from app.models.steel_price_policy import SteelPricePolicy, SteelPriceLadderItem


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

    def get_filter_options(self, db: Session) -> dict[str, list[Any]]:
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
        return {
            "years": years,
            "months": months,
            "steel_mills": steel_mills,
            "category_names": category_names,
            "policy_types": policy_types,
            "grade_types": grade_types,
            "grade_values": grade_values,
        }

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
