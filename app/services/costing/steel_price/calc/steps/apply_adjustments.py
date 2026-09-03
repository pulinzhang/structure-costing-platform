"""加减价匹配：已按大类匹配的行直接落档厚度政策；宽度本期下线。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.yishiyiyi import SteelPricePolicy
from app.repositories.yishiyiyi.policy import SteelPricePolicyRepository
from app.schemas.vo.steel_grade_category_vo import SteelGradeCategoryVO
from app.services.costing.steel_price.calc.models import CalcRow, SteelPriceCalcRequest
from app.services.costing.steel_price.calc.steps.adjustments.thickness import (
    ThicknessAdjustmentMatcher,
)
from app.services.yishiyiyi.steel_grade_category import SteelGradeCategoryService
from app.services.yishiyiyi.steel_grade_category.constants import as_canonical_category


class AdjustmentApplier:
    """加减价编排：仅厚度一步；政策由编排器一次性加载后传入。"""

    def __init__(self) -> None:
        self.policy_repository = SteelPricePolicyRepository()
        self.thickness_matcher = ThicknessAdjustmentMatcher()
        self._grade_category_service = SteelGradeCategoryService()

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
        db: Session,
        rows: list[CalcRow],
        policies: list[SteelPricePolicy],
    ) -> list[CalcRow]:
        """厚度加减价：大类 → CATEGORY 政策 → 料厚落档。"""
        grades = sorted({(row.grade or "").strip() for row in rows if (row.grade or "").strip()})
        category_map = {
            (vo.grade or "").strip(): vo
            for vo in self._grade_category_service.map_grades(db, grades).values()
            if (vo.grade or "").strip()
        }
        for row in rows:
            self._apply_thickness_row(row, policies, category_map)
            row.finalize_status()
        return rows

    def apply_width(
        self,
        rows: list[CalcRow],
        policies: list[SteelPricePolicy],
    ) -> list[CalcRow]:
        """宽度加减价本期下线。"""
        del policies
        return rows

    def _apply_thickness_row(
        self,
        row: CalcRow,
        policies: list[SteelPricePolicy],
        category_map: dict[str, SteelGradeCategoryVO],
    ) -> None:
        if not row.steel_mill:
            row.add_message("缺少基价维度，无法匹配厚度加减价政策")
            return

        existing = as_canonical_category(row.category_name)
        if existing:
            row.category_name = existing
            self.thickness_matcher.apply(row, policies)
            return

        grade = (row.grade or "").strip()
        archive = category_map.get(grade)
        category_name = as_canonical_category(
            archive.category_name if archive is not None else None
        )
        if not category_name:
            row.add_message("牌号未分类，无法匹配厚度加减价政策")
            return
        row.category_name = category_name
        self.thickness_matcher.apply(row, policies)
