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
    normalize_steel_mill,
    steel_mill_matches,
)


def _join_names(names: set[str]) -> str:
    return "、".join(sorted(names)) if names else "无"


def _diagnose_missing_thickness_policy(row: CalcRow, policies: list[SteelPricePolicy]) -> str:
    """钢厂名对不上，或该厂没有对应大类块。文案须自含钢厂（会写入 calc_message）。"""
    mill = normalize_steel_mill(row.steel_mill)
    category = (row.category_name or "").strip()
    typed = [
        policy
        for policy in policies
        if policy.policy_type == "THICKNESS"
        and (policy.grade_type or "").strip().upper() == "CATEGORY"
    ]
    if not typed:
        return "本期没有厚度大类政策，无法匹配厚度加减价"

    mill_hits = [policy for policy in typed if steel_mill_matches(mill, policy.steel_mill)]
    if not mill_hits:
        policy_mills = {
            normalize_steel_mill(policy.steel_mill) for policy in typed if policy.steel_mill
        }
        return f"基价钢厂「{mill}」对不上本期厚度政策钢厂（政策钢厂：{_join_names(policy_mills)}）"

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
    mill = normalize_steel_mill(policy.steel_mill) or "未知钢厂"
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
    - 选政策与中标厚度一览相同（钢厂别名 + 大类 + base_thickness 优先，不跨政策回退）
    - 阶梯只按零件实际料厚命中一档
    """

    def apply(self, row: CalcRow, policies: list[SteelPricePolicy]) -> bool:
        """
        在当期政策中匹配厚度加减价并写回 row。

        Returns:
            True 表示命中；False 表示未命中（已写入提示消息）。
        """
        if not (row.category_name or "").strip():
            row.add_message("牌号未分类，无法匹配厚度加减价政策")
            return False

        policy = find_best_thickness_policy(row, policies)
        if policy is None:
            row.add_message(_diagnose_missing_thickness_policy(row, policies))
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
