"""工程变更单与合册校验。"""

from __future__ import annotations

import re

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
    CHANGE_TYPES,
    EC_ADD_VS_REVISE,
    EC_AFTER_ASSEMBLY_EXISTS,
    EC_BEFORE_ASSEMBLY_INVALID,
    EC_BOM_NEW_ROOT,
    EC_CHANGE_ORDER_COLUMNS,
    EC_CHANGE_ORDER_ROW_COUNT,
    EC_CHANGE_ORDER_TYPE_INVALID,
    EC_EFFECTIVE_MISMATCH,
    EC_EFFECTIVE_TOO_EARLY,
    EC_PROJECT_MISMATCH,
    PART_LEVEL_ASSEMBLY,
    PART_LEVEL_L1,
    PART_LEVEL_L2,
    PART_LEVELS,
    bump_letter_version,
)
from app.common.period import format_period, is_in_period, period, previous_month
from app.exceptions.base import BusinessException
from app.models.bom import BomNode
from app.parsers.bom.models import BomParsedNode
from app.parsers.engineering_change.change_order_parser import ChangeOrderRowParsed

_PERIOD_TEXT_RE = re.compile(r"^(\d{4})\s*年\s*(\d{1,2})\s*月$")


def parse_effective_period_text(text: str) -> tuple[int, int]:
    """解析变更单「2025年07月」→ (2025, 7)。"""
    match = _PERIOD_TEXT_RE.match((text or "").strip())
    if not match:
        raise BusinessException(EC_EFFECTIVE_MISMATCH)
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        raise BusinessException(EC_EFFECTIVE_MISMATCH)
    return year, month


def validate_change_order_rows(
    change_orders: list[ChangeOrderRowParsed],
    *,
    page_vehicle_model: str,
    page_effective_year: int,
    page_effective_month: int,
) -> tuple[int, int]:
    """校验整本变更单：至少一行；项目/生效年月相同；前后总成不重复。"""
    if not change_orders:
        raise BusinessException(EC_CHANGE_ORDER_ROW_COUNT)
    periods: set[tuple[int, int]] = set()
    projects: set[str] = set()
    before_numbers: list[str] = []
    after_numbers: list[str] = []
    for change_order in change_orders:
        year, month = validate_change_order_row(
            change_order,
            page_vehicle_model=page_vehicle_model,
            page_effective_year=page_effective_year,
            page_effective_month=page_effective_month,
        )
        periods.add((year, month))
        projects.add(change_order.project_code.strip().upper())
        before_numbers.append(change_order.before_assembly_part_number.strip())
        if change_order.after_assembly_part_number:
            after_numbers.append(change_order.after_assembly_part_number.strip())
    if len(projects) != 1:
        raise BusinessException(EC_PROJECT_MISMATCH)
    if len(periods) != 1:
        raise BusinessException(EC_EFFECTIVE_MISMATCH)
    if len(before_numbers) != len(set(before_numbers)):
        raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
    if len(after_numbers) != len(set(after_numbers)):
        raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
    year, month = next(iter(periods))
    return year, month


def validate_bom_l0_matches_change_orders(
    parsed_nodes: list[BomParsedNode],
    change_orders: list[ChangeOrderRowParsed],
) -> None:
    """材料清单全部 L0 = 非完成停止变更单行的变更后总成；完成停止的总成不得出现。"""
    file_l0 = {
        (node.part_number or "").strip()
        for node in parsed_nodes
        if node.level == 0 and (node.part_number or "").strip()
    }
    expected = {
        (change_order.after_assembly_part_number or "").strip()
        for change_order in change_orders
        if change_order.change_type != CHANGE_TYPE_STOP and change_order.after_assembly_part_number
    }
    if file_l0 != expected:
        raise BusinessException(EC_BOM_NEW_ROOT)
    stop_numbers = {
        change_order.before_assembly_part_number.strip()
        for change_order in change_orders
        if change_order.change_type == CHANGE_TYPE_STOP
    }
    if file_l0 & stop_numbers:
        raise BusinessException(EC_BOM_NEW_ROOT)


def validate_change_order_row(
    change_order: ChangeOrderRowParsed,
    *,
    page_vehicle_model: str,
    page_effective_year: int,
    page_effective_month: int,
) -> tuple[int, int]:
    """校验变更单行基础规则；返回解析后的生效年月。"""
    if change_order.change_type not in CHANGE_TYPES:
        raise BusinessException(EC_CHANGE_ORDER_TYPE_INVALID)
    if change_order.part_level not in PART_LEVELS:
        raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
    if not change_order.before_assembly_part_number:
        raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
    if change_order.project_code.strip().upper() != page_vehicle_model.strip().upper():
        raise BusinessException(EC_PROJECT_MISMATCH)

    year, month = parse_effective_period_text(change_order.effective_period_text)
    if year != page_effective_year or month != page_effective_month:
        raise BusinessException(
            f"{EC_EFFECTIVE_MISMATCH}：工程变更单 {format_period(year, month)}，"
            f"上传页 {format_period(page_effective_year, page_effective_month)}"
        )

    _validate_columns_by_type(change_order)
    return year, month


def _validate_columns_by_type(change_order: ChangeOrderRowParsed) -> None:
    change_type = change_order.change_type
    if change_type == CHANGE_TYPE_STOP:
        if change_order.part_level != PART_LEVEL_ASSEMBLY:
            raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        if change_order.after_assembly_part_number:
            raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        if (
            change_order.before_part_number
            or change_order.after_part_number
            or change_order.part_name
        ):
            raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        return

    if not change_order.after_assembly_part_number:
        raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
    expected_after = bump_letter_version(change_order.before_assembly_part_number)
    if change_order.after_assembly_part_number != expected_after:
        raise BusinessException(EC_CHANGE_ORDER_COLUMNS)

    if change_type == CHANGE_TYPE_REVISE:
        if change_order.part_level == PART_LEVEL_ASSEMBLY:
            if (
                change_order.before_part_number
                or change_order.after_part_number
                or change_order.part_name
            ):
                raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        else:
            if not change_order.before_part_number or not change_order.after_part_number:
                raise BusinessException(EC_ADD_VS_REVISE)
            if (
                bump_letter_version(change_order.before_part_number)
                != change_order.after_part_number
            ):
                raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        return

    if change_type == CHANGE_TYPE_ADD_PART:
        if change_order.part_level not in {PART_LEVEL_L1, PART_LEVEL_L2}:
            raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        if change_order.before_part_number:
            raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        if not change_order.after_part_number:
            raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        if change_order.after_part_number == change_order.after_assembly_part_number:
            raise BusinessException(EC_ADD_VS_REVISE)
        return

    if change_type == CHANGE_TYPE_NOT_INSTALL:
        if change_order.part_level not in {PART_LEVEL_L1, PART_LEVEL_L2}:
            raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        if not change_order.before_part_number:
            raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        if change_order.after_part_number:
            raise BusinessException(EC_CHANGE_ORDER_COLUMNS)
        return

    raise BusinessException(EC_CHANGE_ORDER_TYPE_INVALID)


def validate_before_assembly_active(
    root: BomNode | None,
    *,
    effective_year: int,
    effective_month: int,
) -> BomNode:
    """
    变更前总成须存在且在切点前一月仍有效；生效月须晚于旧总成生效月。

    切点前一月须有效：合册生效月才「切」旧树，前一月旧月账仍要看见 AA。
    切点当月若仍有效也可：导入瞬间旧树尚未被标失效。
    """
    if root is None or root.level != 0:
        raise BusinessException(EC_BEFORE_ASSEMBLY_INVALID)
    prev_year, prev_month = previous_month(effective_year, effective_month)
    if not is_in_period(
        effective_year=root.effective_year,
        effective_month=root.effective_month,
        expiry_year=root.expiry_year,
        expiry_month=root.expiry_month,
        as_of_year=prev_year,
        as_of_month=prev_month,
    ) and not is_in_period(
        effective_year=root.effective_year,
        effective_month=root.effective_month,
        expiry_year=root.expiry_year,
        expiry_month=root.expiry_month,
        as_of_year=effective_year,
        as_of_month=effective_month,
    ):
        raise BusinessException(EC_BEFORE_ASSEMBLY_INVALID)
    if period(effective_year, effective_month) <= period(root.effective_year, root.effective_month):
        raise BusinessException(EC_EFFECTIVE_TOO_EARLY)
    return root


def validate_after_assembly_absent(existing: BomNode | None) -> None:
    if existing is not None:
        raise BusinessException(EC_AFTER_ASSEMBLY_EXISTS, code=409)
