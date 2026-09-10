"""中标钢厂厚度价格一览：基价表驱动 × 档案大类 × CATEGORY 厚度政策。"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.exceptions.base import BusinessException
from app.models.yishiyiyi import SteelBasePrice, SteelPriceLadderItem, SteelPricePolicy
from app.repositories.masterdata.steel_grade_category import SteelGradeCategoryRepository
from app.repositories.yishiyiyi.base_price import SteelBasePriceRepository
from app.repositories.yishiyiyi.policy import SteelPricePolicyRepository
from app.schemas.vo.winning_thickness_vo import WinningThicknessRowVO
from app.services.masterdata.location.location_service import LocationService
from app.services.yishiyiyi.policy.export.excel_exporter import format_interval
from app.services.yishiyiyi.policy.match.adjustment_common import (
    PolicyMatchContext,
    find_best_thickness_policy,
    normalize_steel_mill,
)

logger = logging.getLogger("service.winning_thickness.assemble")

LadderCacheKey = tuple[str, str, Decimal | None]


def dedupe_bases_by_mill_grade(bases: Sequence[SteelBasePrice]) -> list[SteelBasePrice]:
    """同一牌号+钢厂只保留一条基价（规格不同取先出现行）。"""
    seen: set[tuple[str, str]] = set()
    result: list[SteelBasePrice] = []
    for base in bases:
        key = (
            (base.grade or "").strip(),
            normalize_steel_mill(base.steel_mill),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(base)
    return result


@dataclass(frozen=True, slots=True)
class _BaseContext:
    """组装行所需的基价上下文（仅来自基价表）。"""

    grade: str
    steel_mill: str
    location: str
    year: int
    month: int
    base_price: Decimal
    processing_fee: Decimal
    thick: Decimal | None
    spec: str | None
    base_price_id: int | None = None
    base_excel_filename: str | None = None
    base_sheet_name: str | None = None
    base_excel_row: int | None = None
    base_excel_col: int | None = None

    @classmethod
    def from_orm(cls, base: SteelBasePrice) -> _BaseContext:
        return cls(
            grade=(base.grade or "").strip(),
            steel_mill=base.steel_mill or "",
            location=base.location or "",
            year=int(base.year),
            month=int(base.month),
            base_price=Decimal(str(base.base_price or 0)),
            processing_fee=Decimal(str(base.processing_fee or 0)),
            thick=base.thick if base.thick is not None else None,
            spec=base.spec,
            base_price_id=base.id,
            base_excel_filename=base.excel_filename,
            base_sheet_name=base.sheet_name,
            base_excel_row=base.excel_row,
            base_excel_col=base.excel_col,
        )


class WinningThicknessRowAssembler:
    """
    按基地/年/月组装厚度价格一览行。

    以基价表为据：未定基价的牌号不输出（无基价则厚度加减价无意义）。
    厚度政策按牌号分类档案的大类命中 CATEGORY 政策，同大类各牌号共用阶梯并逐牌号展开。
    """

    def __init__(self) -> None:
        self.base_repository = SteelBasePriceRepository()
        self.policy_repository = SteelPricePolicyRepository()
        self.grade_category_repository = SteelGradeCategoryRepository()

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
            raise BusinessException("基地不能为空")
        locations = LocationService().expand_for_query(db, location)
        if not locations:
            return []

        grade_filter = grade.strip() if grade else None
        category_filter = category_name.strip() if category_name else None

        archive_rows = self.grade_category_repository.list_for_export(
            db,
            grade=grade_filter,
            category_name=category_filter,
        )
        archive_by_grade = {
            (row.grade or "").strip(): row
            for row in archive_rows
            if row.category_name and (row.grade or "").strip()
        }

        bases = self.base_repository.list_for_export(
            db,
            year=year,
            month=month,
            locations=locations,
            steel_mill=steel_mill.strip() if steel_mill else None,
            grade=grade_filter,
        )
        policies = self.policy_repository.list_for_period(db, year=year, month=month)
        ladder_cache: dict[
            LadderCacheKey, tuple[SteelPricePolicy | None, list[SteelPriceLadderItem]]
        ] = {}

        rows: list[WinningThicknessRowVO] = []
        for base in dedupe_bases_by_mill_grade(bases):
            grade_key = (base.grade or "").strip()
            if not grade_key:
                continue

            archive = archive_by_grade.get(grade_key)
            if archive is None:
                continue

            context = _BaseContext.from_orm(base)
            rows.extend(
                self._expand_grade_ladder(
                    context,
                    policies,
                    category_name=archive.category_name,
                    ladder_cache=ladder_cache,
                )
            )

        rows.sort(
            key=lambda r: (
                r.location or "",
                r.category_name or "",
                r.grade or "",
                normalize_steel_mill(r.steel_mill),
                r.thick_min if r.thick_min is not None else Decimal("-1"),
                r.thickness_ladder_item_id or 0,
            )
        )
        logger.info(
            "中标钢厂厚度价格一览组装完成: year=%s month=%s location=%s "
            "bases=%d archive_grades=%d rows=%d",
            year,
            month,
            location,
            len(bases),
            len(archive_by_grade),
            len(rows),
        )
        return rows

    def _expand_grade_ladder(
        self,
        context: _BaseContext,
        policies: list[SteelPricePolicy],
        *,
        category_name: str,
        ladder_cache: dict[
            LadderCacheKey, tuple[SteelPricePolicy | None, list[SteelPriceLadderItem]]
        ],
    ) -> list[WinningThicknessRowVO]:
        policy, items = self._resolve_thickness_ladder(
            policies,
            steel_mill=context.steel_mill,
            category_name=category_name,
            base_thickness=context.thick,
            ladder_cache=ladder_cache,
        )
        return self._rows_from_ladder(
            context,
            category_name=category_name,
            policy=policy,
            items=items,
        )

    def _resolve_thickness_ladder(
        self,
        policies: list[SteelPricePolicy],
        *,
        steel_mill: str,
        category_name: str,
        base_thickness: Decimal | None,
        ladder_cache: dict[
            LadderCacheKey, tuple[SteelPricePolicy | None, list[SteelPriceLadderItem]]
        ],
    ) -> tuple[SteelPricePolicy | None, list[SteelPriceLadderItem]]:
        cache_key: LadderCacheKey = (
            normalize_steel_mill(steel_mill),
            category_name,
            base_thickness,
        )
        if cache_key in ladder_cache:
            return ladder_cache[cache_key]

        policy = self._find_best_thickness_policy(
            steel_mill=steel_mill,
            category_name=category_name,
            base_thickness=base_thickness,
            policies=policies,
        )
        if policy is None:
            ladder_cache[cache_key] = (None, [])
            return None, []

        items = [
            item
            for item in (policy.items or [])
            if item.thick_min is not None or item.thick_max is not None
        ]
        items.sort(key=lambda x: (x.sort_order or 0, x.id or 0))
        ladder_cache[cache_key] = (policy, items)
        return policy, items

    def _rows_from_ladder(
        self,
        context: _BaseContext,
        *,
        category_name: str,
        policy: SteelPricePolicy | None,
        items: list[SteelPriceLadderItem],
    ) -> list[WinningThicknessRowVO]:
        """每个有基价的牌号按政策阶梯展开多行；无政策或无区间则不输出。"""
        if policy is None or not items:
            return []

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
                    context,
                    adjustment,
                    thickness_range,
                    policy,
                    item,
                    category_name=category_name,
                )
            )
        return rows

    def _find_best_thickness_policy(
        self,
        *,
        steel_mill: str,
        category_name: str,
        base_thickness: Decimal | None,
        policies: list[SteelPricePolicy],
    ) -> SteelPricePolicy | None:
        if not steel_mill or not category_name:
            return None

        match_row = PolicyMatchContext(
            grade="",
            thickness=base_thickness if base_thickness is not None else Decimal("0"),
            steel_mill=steel_mill,
            category_name=category_name,
            base_thickness=base_thickness,
        )
        return find_best_thickness_policy(match_row, policies)

    @staticmethod
    def _make_row(
        context: _BaseContext,
        adjustment: Decimal,
        thickness_range: str,
        policy: SteelPricePolicy | None,
        item: SteelPriceLadderItem | None,
        *,
        category_name: str,
    ) -> WinningThicknessRowVO:
        final_price = context.base_price + adjustment + context.processing_fee
        return WinningThicknessRowVO(
            base_price=context.base_price,
            thickness_adjustment=adjustment,
            processing_fee=context.processing_fee,
            final_price=final_price,
            category_name=category_name,
            steel_mill=context.steel_mill,
            thickness_range=thickness_range,
            thick_min=item.thick_min if item is not None else None,
            thick_min_operator=item.thick_min_operator if item is not None else None,
            thick_max=item.thick_max if item is not None else None,
            thick_max_operator=item.thick_max_operator if item is not None else None,
            grade=context.grade,
            year=context.year,
            month=context.month,
            location=context.location,
            spec=context.spec,
            base_thickness=context.thick,
            base_price_id=context.base_price_id,
            base_excel_filename=context.base_excel_filename,
            base_sheet_name=context.base_sheet_name,
            base_excel_row=context.base_excel_row,
            base_excel_col=context.base_excel_col,
            thickness_policy_id=policy.id if policy else None,
            thickness_ladder_item_id=item.id if item else None,
            thickness_excel_filename=policy.excel_filename if policy else None,
            thickness_excel_row=item.excel_row if item else None,
            thickness_excel_col=item.excel_col if item else None,
        )
