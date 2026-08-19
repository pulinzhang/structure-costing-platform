"""纯宽度加减价匹配（policy_type = WIDTH）。"""

from __future__ import annotations

from app.models.yishiyiyi import SteelPricePolicy
from app.services.costing.steel_price.calc.models import CalcRow
from app.services.yishiyiyi.policy.match.adjustment_common import (
    apply_hit,
    find_best_hit,
)


class WidthAdjustmentMatcher:
    """
    纯宽度政策匹配。

    - 只认 policy_type = WIDTH
    - 阶梯只按宽度区间匹配，不看厚度
    - grade 按 exact → generic → category 优先级回退（与 find_best_hit 一致）
    """

    def apply(self, row: CalcRow, candidates: list[SteelPricePolicy]) -> bool:
        """
        在候选政策中匹配宽度加减价并写回 row。

        Returns:
            True 表示命中；False 表示未命中（已写入提示消息）。
        """
        if row.width is None:
            row.add_message("缺少宽度，无法匹配宽度加减价")
            return False

        hit = find_best_hit(
            row,
            candidates,
            policy_types=("WIDTH",),
            check_thickness=False,
            check_width=True,
            prefer_base_thickness=False,
        )
        if hit is None:
            row.add_message("未命中宽度加减价政策")
            return False

        apply_hit(row, hit, prefix="width")
        return True
