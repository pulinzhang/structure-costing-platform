"""加减价匹配：厚度 / 宽度分步独立执行（政策只加载一次）。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.steel_price_policy import SteelPricePolicy
from app.repositories.steel_price_policy import SteelPricePolicyRepository
from app.services.steel_price.calc.models import CalcRow, SteelPriceCalcRequest
from app.services.steel_price.calc.steps.adjustments.common import (
    apply_hit,
    filter_candidates,
    find_best_hit,
)
from app.services.steel_price.calc.steps.adjustments.thickness import (
    ThicknessAdjustmentMatcher,
)
from app.services.steel_price.calc.steps.adjustments.width import (
    WidthAdjustmentMatcher,
)


class AdjustmentApplier:
    """加减价编排：厚度一步、宽度一步；政策由编排器一次性加载后传入。"""

    def __init__(self) -> None:
        self.policy_repository = SteelPricePolicyRepository()
        self.thickness_matcher = ThicknessAdjustmentMatcher()
        self.width_matcher = WidthAdjustmentMatcher()

    def load_policies(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
    ) -> list[SteelPricePolicy]:
        """按核价期加载加减价政策（整次计算只应调用一次）。"""
        return self.policy_repository.list_for_period(
            db,
            year=request.year,
            month=request.month,
        )

    def apply_thickness(
        self,
        rows: list[CalcRow],
        policies: list[SteelPricePolicy],
    ) -> list[CalcRow]:
        """Step：厚度加减价（THICKNESS_WIDTH 组合或纯 THICKNESS）。"""
        for row in rows:
            self._apply_thickness_row(row, policies)
        return rows

    def apply_width(
        self,
        rows: list[CalcRow],
        policies: list[SteelPricePolicy],
    ) -> list[CalcRow]:
        """Step：宽度加减价（纯 WIDTH；组合政策已在厚度步写入宽度溯源则跳过）。"""
        for row in rows:
            self._apply_width_row(row, policies)
            row.finalize_status()
        return rows

    def _apply_thickness_row(
        self,
        row: CalcRow,
        policies: list[SteelPricePolicy],
    ) -> None:
        if not row.steel_mill or not row.category_name:
            row.add_message("缺少基价维度，无法匹配厚度加减价政策")
            return

        candidates = filter_candidates(row, policies)
        if not candidates:
            row.add_message("无对应钢厂/大类厚度政策")
            return

        # 厚宽组合政策：一次命中同时写入厚度金额 + 宽度溯源 ID
        combo_hit = find_best_hit(
            row,
            candidates,
            policy_types=("THICKNESS_WIDTH",),
            check_thickness=True,
            check_width=True,
            prefer_base_thickness=True,
        )
        if combo_hit is not None:
            apply_hit(row, combo_hit, prefix="thickness")
            policy, item = combo_hit
            row.width_policy_id = policy.id
            row.width_ladder_item_id = item.id
            row.width_excel_filename = policy.excel_filename
            row.width_excel_row = item.excel_row
            row.width_excel_col = item.excel_col
            return

        self.thickness_matcher.apply(row, candidates)

    def _apply_width_row(
        self,
        row: CalcRow,
        policies: list[SteelPricePolicy],
    ) -> None:
        # 厚度步已通过 THICKNESS_WIDTH 写入宽度溯源，视为已处理
        if row.width_policy_id is not None:
            return

        if not row.steel_mill or not row.category_name:
            row.add_message("缺少基价维度，无法匹配宽度加减价政策")
            return

        candidates = filter_candidates(row, policies)
        if not candidates:
            row.add_message("无对应钢厂/大类宽度政策")
            return

        self.width_matcher.apply(row, candidates)
