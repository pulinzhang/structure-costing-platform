"""纯厚度加减价匹配（policy_type = THICKNESS）。"""

from __future__ import annotations

from app.models.steel_price_policy import SteelPriceLadderItem, SteelPricePolicy
from app.services.steel_price.calc.models import CalcRow
from app.services.steel_price.calc.steps.adjustments.common import (
    PolicyHit,
    apply_hit,
    item_matches_dims,
    to_decimal,
)


class ThicknessAdjustmentMatcher:
    """
    纯厚度政策匹配。

    特殊性（相对宽度 / 厚宽组合）：
    - 只认 policy_type = THICKNESS
    - grade_value 必须与计算行的 grade 完全相等（不做 NULL / CATEGORY 回退）
    - 阶梯只按厚度区间匹配，不看宽度
    - 优先命中 base_thickness 与基价厚一致的政策
    """

    def apply(self, row: CalcRow, candidates: list[SteelPricePolicy]) -> bool:
        """
        在候选政策中匹配厚度加减价并写回 row。

        Returns:
            True 表示命中；False 表示未命中（已写入提示消息）。
        """
        hit = self._find_hit(row, candidates)
        if hit is None:
            row.add_message("未命中厚度加减价政策")
            return False

        apply_hit(row, hit, prefix="thickness")
        return True

    def _find_hit(
        self,
        row: CalcRow,
        candidates: list[SteelPricePolicy],
    ) -> PolicyHit | None:
        grade = (row.grade or "").strip()
        if not grade:
            return None

        # 特殊性：grade_value 必须等于传入牌号，禁止通用/大类回退
        policies = [
            p
            for p in candidates
            if p.policy_type == "THICKNESS"
            and (p.grade_value or "").strip() == grade
        ]
        if not policies:
            return None

        for policy in self._order_by_base_thickness(policies, row):
            item = self._match_thickness_item(policy, row)
            if item is not None:
                return policy, item
        return None

    @staticmethod
    def _order_by_base_thickness(
        policies: list[SteelPricePolicy],
        row: CalcRow,
    ) -> list[SteelPricePolicy]:
        row_base = row.base_thickness
        exact: list[SteelPricePolicy] = []
        nullable: list[SteelPricePolicy] = []
        others: list[SteelPricePolicy] = []
        for policy in policies:
            policy_base = to_decimal(policy.base_thickness)
            if row_base is not None and policy_base is not None and policy_base == row_base:
                exact.append(policy)
            elif policy_base is None:
                nullable.append(policy)
            else:
                others.append(policy)
        return exact + nullable + others

    @staticmethod
    def _match_thickness_item(
        policy: SteelPricePolicy,
        row: CalcRow,
    ) -> SteelPriceLadderItem | None:
        hits: list[SteelPriceLadderItem] = []
        for item in policy.items or []:
            if item_matches_dims(
                item,
                thickness=row.thickness,
                width=None,
                check_thickness=True,
                check_width=False,
            ):
                hits.append(item)
        if not hits:
            return None
        hits.sort(key=lambda x: (x.sort_order or 0, x.id or 0))
        return hits[0]
