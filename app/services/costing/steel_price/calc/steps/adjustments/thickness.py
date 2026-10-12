"""纯厚度加减价匹配（policy_type = THICKNESS，大类 CATEGORY）。"""

from __future__ import annotations

from app.models.yishiyiyi import SteelPricePolicy
from app.services.costing.steel_price.calc.models import CalcRow
from app.services.costing.steel_price.spec_format import format_thickness
from app.services.yishiyiyi.policy.match.adjustment_common import (
    apply_hit,
    find_best_thickness_policy,
    grade_category,
    match_items,
)


def _join_names(names: set[str]) -> str:
    return "、".join(sorted(names)) if names else "无"


def _thickness_category_policies(policies: list[SteelPricePolicy]) -> list[SteelPricePolicy]:
    return [
        policy
        for policy in policies
        if policy.policy_type == "THICKNESS"
        and (policy.grade_type or "").strip().upper() == "CATEGORY"
    ]


def _diagnose_missing_thickness_policy(
    row: CalcRow, policies: list[SteelPricePolicy]
) -> str | None:
    """该厂有厚度块但未命中时给出原因。该厂本期无厚度块则返回 None（按基价计，不报错）。"""
    mill = (row.steel_mill or "").strip() or "未知钢厂"
    category = (row.category_name or "").strip()
    typed = _thickness_category_policies(policies)
    if not typed:
        return "本期没有厚度大类政策，无法匹配厚度加减价"

    mill_hits = [
        policy
        for policy in typed
        if row.steel_mill_id is not None and policy.steel_mill_id == row.steel_mill_id
    ]
    if not mill_hits:
        return None

    if not any(grade_category(policy, row) for policy in mill_hits):
        mill_categories = {
            (policy.category_name or "").strip() for policy in mill_hits if policy.category_name
        }
        return (
            f"钢厂「{mill}」本期厚度政策没有大类「{category}」"
            f"（该厂政策大类：{_join_names(mill_categories)}）"
        )
    return "无对应钢厂/大类厚度政策"


def _ladder_miss_message(row: CalcRow, policy: SteelPricePolicy) -> str:
    mill = (policy.steel_mill or "").strip() or "未知钢厂"
    category = (policy.category_name or "").strip() or "未知大类"
    base_text = (
        format_thickness(policy.base_thickness) if policy.base_thickness is not None else "空"
    )
    thick_text = format_thickness(row.thickness)
    return (
        f"已锁定{mill}·{category}厚度政策（基准厚 {base_text}），"
        f"料厚 {thick_text} 未落入该政策阶梯"
    )


class ThicknessAdjustmentMatcher:
    """
    牌号已由调用方解析为档案大类后：锁定一条 CATEGORY 政策，再按料厚落档。

    - 只认 policy_type = THICKNESS 且 grade_type = CATEGORY
    - 选政策与中标厚度一览相同（钢厂 id + 大类 + base_thickness 优先，不跨政策回退）
    - 阶梯只按零件实际料厚命中一档
    """

    def apply(self, row: CalcRow, policies: list[SteelPricePolicy]) -> bool:
        """
        在当期政策中匹配厚度加减价并写回 row。

        Returns:
            True 表示命中；False 表示未命中。该厂本期无厚度块时不写提示消息。
        """
        if not (row.category_name or "").strip():
            row.add_message("这个牌号还没分类，对不上厚度加减价")
            return False

        policy = find_best_thickness_policy(row, policies)
        if policy is None:
            reason = _diagnose_missing_thickness_policy(row, policies)
            if reason is None:
                row.thickness_applicable = False
                return False
            row.add_message(reason)
            return False

        item = match_items(
            policy,
            thickness=row.thickness,
            width=None,
            check_thickness=True,
            check_width=False,
        )
        if item is None:
            row.add_message(_ladder_miss_message(row, policy))
            return False

        apply_hit(row, (policy, item), prefix="thickness")
        return True
