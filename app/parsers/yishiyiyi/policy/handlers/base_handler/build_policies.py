"""政策构建：块描述 → ParsedPolicy 列表。"""

from __future__ import annotations

from typing import Any

from openpyxl.worksheet.worksheet import Worksheet

from app.common.steel_grade_category import (
    CANONICAL_CATEGORY_NAMES,
    normalize_category_name,
)
from app.exceptions.base import BusinessException
from app.parsers.yishiyiyi.policy.handlers.constants import GRADE_LABELS
from app.parsers.yishiyiyi.policy.models.ladder_item import ParsedLadderItem
from app.parsers.yishiyiyi.policy.models.policy import (
    GRADE_TYPE_CATEGORY,
    POLICY_TYPE_THICKNESS,
    POLICY_TYPE_WIDTH,
    ParsedPolicy,
)

from .build_items import ItemBuilder
from .locate_blocks import BlockLocator
from .sheet_scanner import SheetScanner


class PolicyBuilder:
    """单块装配为 ParsedPolicy；厚度块按大类去重阶梯。"""

    def __init__(
        self,
        scanner: SheetScanner,
        locator: BlockLocator,
        items: ItemBuilder,
    ) -> None:
        self.scanner = scanner
        self._locator = locator
        self._items = items

    @staticmethod
    def _ladder_items_signature(items: list[ParsedLadderItem]) -> tuple[tuple[object, ...], ...]:
        ordered = sorted(items, key=lambda item: (item.sort_order or 0, item.excel_row or 0))
        return tuple(
            (
                item.thick_min,
                item.thick_min_operator,
                item.thick_max,
                item.thick_max_operator,
                item.price_adjustment,
                bool(item.is_base),
            )
            for item in ordered
        )

    def build_policies_from_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: dict[str, Any],
    ) -> list[ParsedPolicy]:
        """给定块描述，构建 ParsedPolicy 列表。"""
        policy_type = block.get("policy_type", POLICY_TYPE_THICKNESS)
        if policy_type == POLICY_TYPE_WIDTH:
            return []
        if policy_type == POLICY_TYPE_THICKNESS:
            return self._build_category_thickness_policies_from_block(sheet, steel_mill, block)
        return self._build_legacy_policies_from_block(sheet, steel_mill, block)

    def _build_category_thickness_policies_from_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: dict[str, Any],
    ) -> list[ParsedPolicy]:
        """厚度块：每个大类一条 CATEGORY 政策（冷轧钢 / 镀锌钢 / 酸洗钢）。"""
        grade_col = block.get("grade_col")
        header_row = block["header_row"]
        price_cols = list(block["price_cols"])
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = (block.get("category_name") or "冷轧钢").strip()
        base_thickness = block.get("base_thickness")
        grade_blacklist = block.get("grade_blacklist", GRADE_LABELS)

        canonical = normalize_category_name(category_name)
        if canonical not in CANONICAL_CATEGORY_NAMES:
            return []

        boundaries = self._locator.collect_boundaries_thickness(sheet, header_row, price_cols)
        if not boundaries:
            return []

        sorted_price_cols = sorted(price_cols)
        representative_items: list[ParsedLadderItem] | None = None
        representative_signature: tuple[tuple[object, ...], ...] | None = None

        for row_index in range(data_start, data_end + 1):
            if grade_col is None:
                continue
            grade = self.scanner.text_or_none(sheet, row_index, grade_col)
            if not grade:
                continue
            if "//" in grade:
                grade = grade.replace("//", "/")
            if grade in grade_blacklist:
                continue

            items, _ = self._items.build_items_for_row(
                sheet,
                row_index,
                sorted_price_cols,
                boundaries,
                POLICY_TYPE_THICKNESS,
                sort_order=row_index,
            )
            if not items:
                continue

            signature = self._ladder_items_signature(items)
            if representative_items is None:
                representative_items = items
                representative_signature = signature
                continue
            if signature != representative_signature:
                raise BusinessException(
                    f"厚度块「{category_name}」多行牌号阶梯不一致（行 {row_index}），请核对 Excel"
                )

        if not representative_items:
            return []

        grade_value = category_name
        return [
            ParsedPolicy(
                steel_mill=steel_mill,
                category_name=category_name,
                grade_type=GRADE_TYPE_CATEGORY,
                grade_value=grade_value,
                policy_type=POLICY_TYPE_THICKNESS,
                base_thickness=base_thickness,
                items=representative_items,
            )
        ]

    def _build_legacy_policies_from_block(
        self,
        sheet: Worksheet,
        steel_mill: str,
        block: dict[str, Any],
    ) -> list[ParsedPolicy]:
        """非厚度块遗留路径（本期应无调用）。"""
        grade_col = block.get("grade_col")
        header_row = block["header_row"]
        price_cols = list(block["price_cols"])
        data_start = block["data_row_start"]
        data_end = block["data_row_end"]
        category_name = block.get("category_name", "冷轧钢")
        base_thickness = block.get("base_thickness")
        grade_blacklist = block.get("grade_blacklist", GRADE_LABELS)
        policy_type = block.get("policy_type", POLICY_TYPE_THICKNESS)

        boundaries = self._locator.collect_boundaries(sheet, header_row, price_cols)
        if not boundaries:
            return []

        sorted_price_cols = sorted(price_cols)
        policies: list[ParsedPolicy] = []

        for r in range(data_start, data_end + 1):
            if grade_col is None:
                continue
            grade = self.scanner.text_or_none(sheet, r, grade_col)
            if not grade:
                continue
            # 钢种列 "B250P1//HC260Y" 可能是操作人员笔误，将 "//" 替换为 "/"
            if "//" in grade:
                grade = grade.replace("//", "/")
            if grade in grade_blacklist:
                continue

            grade_type = self._items.infer_grade_type(grade, policy_type)
            items, _ = self._items.build_items_for_row(
                sheet, r, sorted_price_cols, boundaries, policy_type, sort_order=r
            )
            if not items:
                continue

            policies.append(
                ParsedPolicy(
                    steel_mill=steel_mill,
                    category_name=category_name,
                    grade_type=grade_type,
                    grade_value=grade,
                    policy_type=policy_type,
                    base_thickness=base_thickness,
                    items=items,
                )
            )
        return policies
