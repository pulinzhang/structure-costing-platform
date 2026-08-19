"""
钢价政策阶梯匹配辅助模块
职责：纯匹配逻辑，不涉及数据库操作
"""

from decimal import Decimal
from typing import Optional

from app.models.yishiyiyi import SteelPricePolicy, SteelPriceLadderItem
from app.schemas.dto.steel_price_policy_dto import PolicyMatchRequest


# =============================================================================
# 运算符比较
# =============================================================================

def _compare(value: Optional[Decimal], operator: Optional[str]) -> bool:
    """
    单条件比较：value 是否满足 operator 条件。
    operator 为空或 None 时视为无限制，返回 True。
    """
    if operator is None or value is None:
        return True
    if operator == ">=":
        return value >= Decimal(str(operator).replace(">=", ""))
    if operator == ">":
        return value > Decimal(str(operator).replace(">", ""))
    if operator == "<=":
        return value <= Decimal(str(operator).replace("<=", ""))
    if operator == "<":
        return value < Decimal(str(operator).replace("<", ""))
    return True


def _item_matches(
    item: SteelPriceLadderItem,
    thickness: Optional[Decimal],
    width: Optional[Decimal],
    zinc_coating: Optional[Decimal],
    target_sub_group: Optional[str],
) -> bool:
    """
    判断单条明细是否命中给定的厚度、宽度和锌层克重值。
    - 厚度/宽度/锌层克重为 None 时，该维度不参与匹配
    - target_sub_group 非空时，必须完全匹配
    """
    # 子分组条件
    if item.target_sub_group and target_sub_group:
        if item.target_sub_group != target_sub_group:
            return False
    elif item.target_sub_group and not target_sub_group:
        return False

    # 厚度条件匹配
    if thickness is not None:
        if item.thick_min is not None:
            op = item.thick_min_operator or ">="
            if op == ">=" and not (thickness >= item.thick_min):
                return False
            if op == ">" and not (thickness > item.thick_min):
                return False
        if item.thick_max is not None:
            op = item.thick_max_operator or "<"
            if op == "<=" and not (thickness <= item.thick_max):
                return False
            if op == "<" and not (thickness < item.thick_max):
                return False

    # 宽度条件匹配
    if width is not None:
        if item.width_min is not None:
            op = item.width_min_operator or ">="
            if op == ">=" and not (width >= item.width_min):
                return False
            if op == ">" and not (width > item.width_min):
                return False
        if item.width_max is not None:
            op = item.width_max_operator or "<"
            if op == "<=" and not (width <= item.width_max):
                return False
            if op == "<" and not (width < item.width_max):
                return False

    # 锌层克重条件匹配
    if zinc_coating is not None:
        if item.zinc_coating_min is not None:
            op = item.zinc_coating_min_operator or ">="
            if op == ">=" and not (zinc_coating >= item.zinc_coating_min):
                return False
            if op == ">" and not (zinc_coating > item.zinc_coating_min):
                return False
        if item.zinc_coating_max is not None:
            op = item.zinc_coating_max_operator or "<"
            if op == "<=" and not (zinc_coating <= item.zinc_coating_max):
                return False
            if op == "<" and not (zinc_coating < item.zinc_coating_max):
                return False

    return True


# =============================================================================
# 匹配器类
# =============================================================================

class LadderMatcher:
    """阶梯明细匹配器"""

    def collect_hits(
        self,
        candidates: list[SteelPricePolicy],
        data: PolicyMatchRequest,
    ) -> list[tuple[SteelPriceLadderItem, int]]:
        """从候选政策中收集所有匹配项。"""
        hits: list[tuple[SteelPriceLadderItem, int]] = []
        for policy in candidates:
            for item in policy.items:
                if _item_matches(
                    item,
                    thickness=getattr(data, "thickness", None),
                    width=getattr(data, "width", None),
                    zinc_coating=getattr(data, "zinc_coating", None),
                    target_sub_group=data.target_sub_group,
                ):
                    hits.append((item, policy.id))
        return hits

    def sort_hits(
        self,
        hits: list[tuple[SteelPriceLadderItem, int]],
    ) -> list[tuple[SteelPriceLadderItem, int]]:
        """按 sort_order 和 id 排序匹配结果"""
        return sorted(hits, key=lambda x: (x[0].sort_order, x[0].id))
