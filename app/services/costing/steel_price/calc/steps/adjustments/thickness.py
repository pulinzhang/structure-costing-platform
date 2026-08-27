"""纯厚度加减价匹配（policy_type = THICKNESS，大类 CATEGORY）。"""

from __future__ import annotations

from app.models.yishiyiyi import SteelPricePolicy
from app.services.costing.steel_price.calc.models import CalcRow
from app.services.yishiyiyi.policy.match.adjustment_common import (
    apply_hit,
    find_best_thickness_policy,
    match_items,
)


class ThicknessAdjustmentMatcher:
    """
    牌号已由调用方解析为档案大类后：锁定一条 CATEGORY 政策，再按料厚落档。

    - 只认 policy_type = THICKNESS 且 grade_type = CATEGORY
    - 选政策与中标厚度一览相同（钢厂别名 + 大类 + base_thickness 优先，不跨政策回退）
    - 阶梯只按零件实际料厚命中一档
    """

    def apply(self, row: CalcRow, policies: list[SteelPricePolicy]) -> bool:
        """
        在当期政策中匹配厚度加减价并写回 row。

        Returns:
            True 表示命中；False 表示未命中（已写入提示消息）。
        """
        if not (row.grade or "").strip() or not (row.category_name or "").strip():
            row.add_message("牌号未分类，无法匹配厚度加减价政策")
            return False

        policy = find_best_thickness_policy(row, policies)
        if policy is None:
            row.add_message("无对应钢厂/大类厚度政策")
            return False

        item = match_items(
            policy,
            thickness=row.thickness,
            width=None,
            check_thickness=True,
            check_width=False,
        )
        if item is None:
            row.add_message("未命中厚度加减价政策")
            return False

        apply_hit(row, (policy, item), prefix="thickness")
        return True
