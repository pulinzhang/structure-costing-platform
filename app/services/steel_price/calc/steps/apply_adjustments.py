"""Step3：一次加载政策后，在内存中匹配厚/宽加减价。"""

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


class AdjustmentApplier:
    """加减价编排：一次取政策，再委托各维度匹配器。"""

    def __init__(self) -> None:
        self.policy_repository = SteelPricePolicyRepository()
        self.thickness_matcher = ThicknessAdjustmentMatcher()

    def apply(
        self,
        db: Session,
        request: SteelPriceCalcRequest,
        rows: list[CalcRow],
    ) -> list[CalcRow]:
        policies = self.policy_repository.list_for_period(
            db,
            year=request.year,
            month=request.month,
        )
        for row in rows:
            self._apply_row(row, policies)
            row.finalize_status()
        return rows

    def _apply_row(self, row: CalcRow, policies: list[SteelPricePolicy]) -> None:
        if not row.steel_mill or not row.category_name:
            row.add_message("缺少基价维度，无法匹配加减价政策")
            return

        candidates = filter_candidates(row, policies)
        if not candidates:
            row.add_message("无对应钢厂/大类政策")
            return

        # 1) 厚宽组合政策（后续再拆）
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

        # 2) 纯厚度政策
        self.thickness_matcher.apply(row, candidates)

        # 3) 纯宽度政策（后续再拆）
        if row.width is None:
            row.add_message("缺少宽度，无法匹配宽度加减价")
            return

        width_hit = find_best_hit(
            row,
            candidates,
            policy_types=("WIDTH",),
            check_thickness=False,
            check_width=True,
            prefer_base_thickness=False,
        )
        if width_hit is None:
            row.add_message("未命中宽度加减价政策")
            return
        apply_hit(row, width_hit, prefix="width")
