"""钢价政策写入：主表 / 明细 / 条件批量删除。"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.yishiyiyi import SteelPriceLadderItem, SteelPricePolicy
from app.repositories.persist import apply_dto_fields, model_from_payload
from app.repositories.yishiyiyi.policy.queries import SteelPricePolicyQueries
from app.schemas.dto.steel_price_policy_dto import (
    LadderItemUpdate,
    PolicyUpdate,
    SteelPriceLadderItemWrite,
    SteelPricePolicyWrite,
)


class SteelPricePolicyWrites:
    def __init__(self, queries: SteelPricePolicyQueries | None = None) -> None:
        self._queries = queries or SteelPricePolicyQueries()

    """主表与明细写操作；不 commit。"""

    def create_policy(self, db: Session, data: SteelPricePolicyWrite) -> SteelPricePolicy:
        """
        创建政策主表记录（不含明细）。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        policy = model_from_payload(SteelPricePolicy, data)
        db.add(policy)
        return policy

    def update_policy(
        self,
        db: Session,
        policy_id: int,
        update_data: PolicyUpdate,
        *,
        updated_by: str,
    ) -> SteelPricePolicy | None:
        """
        按主键更新政策主表字段，返回更新后记录或 None（不存在）。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        policy = self._queries.get_by_id(db, policy_id, load_items=False)
        if policy is None:
            return None
        apply_dto_fields(policy, update_data, skip=frozenset({"items"}))
        policy.updated_by = updated_by
        return policy

    def delete_policy(self, db: Session, policy_id: int) -> bool:
        """
        按主键删除政策（含级联明细）。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        policy = self._queries.get_by_id(db, policy_id, load_items=False)
        if policy is None:
            return False
        db.delete(policy)
        return True

    def add_items(
        self,
        db: Session,
        policy_id: int,
        items_data: list[SteelPriceLadderItemWrite],
    ) -> list[SteelPriceLadderItem]:
        """
        批量新增明细。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        created: list[SteelPriceLadderItem] = []
        for item_data in items_data:
            item = model_from_payload(SteelPriceLadderItem, item_data)
            item.policy_id = policy_id
            db.add(item)
            created.append(item)
        return created

    def update_item(
        self,
        db: Session,
        item_id: int,
        update_data: LadderItemUpdate,
        *,
        updated_by: str,
    ) -> SteelPriceLadderItem | None:
        """
        更新单条明细。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        item = db.query(SteelPriceLadderItem).filter(SteelPriceLadderItem.id == item_id).first()
        if item is None:
            return None
        apply_dto_fields(item, update_data)
        item.updated_by = updated_by
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
        new_items_data: list[SteelPriceLadderItemWrite],
    ) -> list[SteelPriceLadderItem]:
        """
        整组替换政策下的全部明细（旧明细级联删除）。
        注意：此方法不 flush，由调用方（Service）控制事务。
        """
        self.delete_items_by_policy_id(db, policy_id)
        return self.add_items(db, policy_id, new_items_data)

    def count_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
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
        if steel_mill_id is not None:
            query = query.filter(SteelPricePolicy.steel_mill_id == steel_mill_id)
        elif steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == steel_mill)

        return query.scalar() or 0

    def delete_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
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
            steel_mill_id=steel_mill_id,
        )
        query = db.query(SteelPricePolicy)

        if year is not None:
            query = query.filter(SteelPricePolicy.year == year)
        if month is not None:
            query = query.filter(SteelPricePolicy.month == month)
        if steel_mill_id is not None:
            query = query.filter(SteelPricePolicy.steel_mill_id == steel_mill_id)
        elif steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == steel_mill)

        query.delete(synchronize_session=False)
        return count

    def get_policy_ids_by_conditions(
        self,
        db: Session,
        *,
        year: int | None = None,
        month: int | None = None,
        steel_mill: str | None = None,
        steel_mill_id: int | None = None,
    ) -> list[int]:
        """
        根据条件获取政策 ID 列表（用于级联删除前的预处理）。
        """
        query = db.query(SteelPricePolicy.id)

        if year is not None:
            query = query.filter(SteelPricePolicy.year == year)
        if month is not None:
            query = query.filter(SteelPricePolicy.month == month)
        if steel_mill_id is not None:
            query = query.filter(SteelPricePolicy.steel_mill_id == steel_mill_id)
        elif steel_mill:
            query = query.filter(SteelPricePolicy.steel_mill == steel_mill)

        return [row[0] for row in query.all()]
