"""中标钢厂厚度价格一览：基价 × 厚度阶梯行组装。"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.steel_base_price import SteelBasePrice
from app.models.steel_price_policy import SteelPriceLadderItem, SteelPricePolicy
from app.repositories.yishiyiyi.base_price import SteelBasePriceRepository
from app.repositories.yishiyiyi.policy import SteelPricePolicyRepository
from app.schemas.vo.winning_thickness_vo import WinningThicknessRowVO
from app.services.costing.steel_price.calc.models import CalcRow
from app.services.costing.steel_price.calc.steps.adjustments.common import (
    filter_candidates,
    normalize_steel_mill,
    order_by_base_thickness,
)
from app.services.yishiyiyi.policy.export.excel_exporter import format_interval

logger = logging.getLogger("service.winning_thickness.assemble")


class WinningThicknessRowAssembler:
    """按基地/年/月组装厚度价格一览行。"""

    def __init__(self) -> None:
        self.base_repository = SteelBasePriceRepository()
        self.policy_repository = SteelPricePolicyRepository()

    def build_rows(
        self,
        db: Session,
        *,
        year: int,
        month: int,
        location: str,
        steel_mill: str | None = None,
        category_name: str | None = None,
        grade: str | None = None,
    ) -> list[WinningThicknessRowVO]:
        location = (location or "").strip()
        if not location:
            raise ValueError("基地不能为空")

        bases = self.base_repository.list_for_export(
            db,
            year=year,
            month=month,
            location=location,
            steel_mill=steel_mill.strip() if steel_mill else None,
            category_name=category_name.strip() if category_name else None,
            grade=grade.strip() if grade else None,
        )
        policies = self.policy_repository.list_for_period(db, year=year, month=month)

        unique_bases = self._dedupe_bases(bases)
        rows: list[WinningThicknessRowVO] = []
        for base in unique_bases:
            rows.extend(self._expand_base(base, policies))

        rows.sort(
            key=lambda r: (
                r.location or "",
                r.category_name or "",
                r.grade or "",
                normalize_steel_mill(r.steel_mill),
                r.thickness_range or "",
            )
        )
        logger.info(
            "中标钢厂厚度价格一览组装完成: year=%s month=%s location=%s bases=%d rows=%d",
            year,
            month,
            location,
            len(unique_bases),
            len(rows),
        )
        return rows

    @staticmethod
    def _dedupe_bases(bases: list[SteelBasePrice]) -> list[SteelBasePrice]:
        seen: set[tuple[str, str, str]] = set()
        result: list[SteelBasePrice] = []
        for base in bases:
            key = (
                (base.grade or "").strip(),
                normalize_steel_mill(base.steel_mill),
                (base.category_name or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(base)
        return result

    def _expand_base(
        self,
        base: SteelBasePrice,
        policies: list[SteelPricePolicy],
    ) -> list[WinningThicknessRowVO]:
        base_price = Decimal(str(base.base_price or 0))
        policy = self._find_best_thickness_policy(base, policies)
        if policy is None:
            return [self._make_row(base, base_price, Decimal("0"), "-", None, None)]

        items = [
            item
            for item in (policy.items or [])
            if item.thick_min is not None or item.thick_max is not None
        ]
        if not items:
            return [self._make_row(base, base_price, Decimal("0"), "-", policy, None)]

        items.sort(key=lambda x: (x.sort_order or 0, x.id or 0))
        rows: list[WinningThicknessRowVO] = []
        for item in items:
            adjustment = Decimal(str(item.price_adjustment or 0))
            thickness_range = format_interval(
                "t",
                item.thick_min,
                item.thick_min_operator,
                item.thick_max,
                item.thick_max_operator,
                decimals=2,
            )
            rows.append(
                self._make_row(
                    base,
                    base_price,
                    adjustment,
                    thickness_range,
                    policy,
                    item,
                )
            )
        return rows

    def _find_best_thickness_policy(
        self,
        base: SteelBasePrice,
        policies: list[SteelPricePolicy],
    ) -> SteelPricePolicy | None:
        grade = (base.grade or "").strip()
        if not grade or not base.steel_mill or not base.category_name:
            return None

        calc_row = CalcRow(
            year=int(base.year),
            month=int(base.month),
            location=base.location or "",
            grade=grade,
            thickness=Decimal(str(base.thick)) if base.thick is not None else Decimal("0"),
            steel_mill=base.steel_mill,
            category_name=base.category_name,
            base_thickness=(
                Decimal(str(base.thick)) if base.thick is not None else None
            ),
            base_price=Decimal(str(base.base_price or 0)),
            base_price_id=base.id,
        )
        candidates = filter_candidates(calc_row, policies)
        thickness_policies = [
            p
            for p in candidates
            if p.policy_type == "THICKNESS"
            and (p.grade_value or "").strip() == grade
        ]
        if not thickness_policies:
            return None

        ordered = order_by_base_thickness(
            thickness_policies,
            calc_row,
            prefer_base_thickness=True,
        )
        return ordered[0] if ordered else None

    @staticmethod
    def _make_row(
        base: SteelBasePrice,
        base_price: Decimal,
        adjustment: Decimal,
        thickness_range: str,
        policy: SteelPricePolicy | None,
        item: SteelPriceLadderItem | None,
    ) -> WinningThicknessRowVO:
        processing_fee = Decimal(str(base.processing_fee or 0))
        final_price = base_price + adjustment + processing_fee
        return WinningThicknessRowVO(
            base_price=float(base_price),
            thickness_adjustment=float(adjustment),
            processing_fee=float(processing_fee),
            final_price=float(final_price),
            category_name=base.category_name or "",
            steel_mill=base.steel_mill or "",
            thickness_range=thickness_range,
            grade=base.grade or "",
            year=int(base.year),
            month=int(base.month),
            location=base.location or "",
            spec=base.spec,
            base_thickness=float(base.thick) if base.thick is not None else None,
            base_price_id=base.id,
            base_excel_filename=base.excel_filename,
            base_sheet_name=base.sheet_name,
            base_excel_row=base.excel_row,
            base_excel_col=base.excel_col,
            thickness_policy_id=policy.id if policy else None,
            thickness_ladder_item_id=item.id if item else None,
            thickness_excel_filename=policy.excel_filename if policy else None,
            thickness_excel_row=item.excel_row if item else None,
            thickness_excel_col=item.excel_col if item else None,
        )
