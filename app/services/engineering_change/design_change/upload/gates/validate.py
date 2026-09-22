"""工程变更单与工程变更校验。"""

from __future__ import annotations

import re
from collections.abc import Sequence

from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_NOT_INSTALL,
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
    CHANGE_TYPES,
    EC_ADD_ALREADY_ON_TREE,
    EC_ADD_VS_REVISE,
    EC_AFTER_ASSEMBLY_EXISTS,
    EC_BEFORE_ASSEMBLY_INVALID,
    EC_BOM_NEW_ROOT,
    EC_CHANGE_ORDER_ASSEMBLY_REPEAT,
    EC_CHANGE_ORDER_COLUMNS,
    EC_CHANGE_ORDER_ROW_COUNT,
    EC_CHANGE_ORDER_TYPE_INVALID,
    EC_EFFECTIVE_MISMATCH,
    EC_EFFECTIVE_TOO_EARLY,
    EC_PART_NOT_ON_TREE,
    EC_PROJECT_MISMATCH,
    PART_LEVEL_ASSEMBLY,
    PART_LEVEL_L1,
    PART_LEVEL_L2,
    PART_LEVEL_TO_BOM_LEVEL,
    PART_LEVELS,
    listed,
    quoted,
)
from app.common.period import format_period, is_in_period, period, previous_month
from app.exceptions.base import BusinessException
from app.models.bom import BomNode
from app.parsers.bom.bom_parser import BomParsedNode
from app.parsers.engineering_change.design_change.change_order_parser import ChangeOrderRowParsed

_PERIOD_TEXT_RE = re.compile(r"^(\d{4})\s*年\s*(\d{1,2})\s*月$")


def _row(change_order: ChangeOrderRowParsed) -> str:
    return f"工程变更单第 {change_order.excel_row} 行"


def parse_effective_period_text(text: str) -> tuple[int, int]:
    """解析变更单「2025年07月」→ (2025, 7)。"""
    raw = (text or "").strip()
    match = _PERIOD_TEXT_RE.match(raw)
    if not match:
        raise BusinessException(
            f"{EC_EFFECTIVE_MISMATCH}：工程变更单写成{quoted(raw)}，请写成「2025年07月」这种。"
        )
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        raise BusinessException(
            f"{EC_EFFECTIVE_MISMATCH}：工程变更单月份 {month} 无效，请写成 1–12 月。"
        )
    return year, month


def validate_change_order_rows(
    change_orders: list[ChangeOrderRowParsed],
    *,
    page_vehicle_model: str,
    page_effective_year: int,
    page_effective_month: int,
) -> tuple[int, int]:
    """工程变更单表内门禁：先项目与变更年月，再变更前/后总成唯一（多场景须合并单元格）。"""
    if not change_orders:
        raise BusinessException(f"{EC_CHANGE_ORDER_ROW_COUNT}。工程变更单表头下面没有数据行。")
    year, month = validate_change_order_project(
        change_orders,
        page_vehicle_model=page_vehicle_model,
        page_effective_year=page_effective_year,
        page_effective_month=page_effective_month,
    )
    for change_order in change_orders:
        validate_change_order_row_shape(change_order)
    _assert_unique_assemblies(change_orders)
    return year, month


def validate_change_order_project(
    change_orders: list[ChangeOrderRowParsed],
    *,
    page_vehicle_model: str,
    page_effective_year: int,
    page_effective_month: int,
) -> tuple[int, int]:
    """第一道：项目与上传页一致；一次上传只能有一个变更年月，且须等于上传页。"""
    page_project = page_vehicle_model.strip().upper()
    projects: set[str] = set()
    periods: set[tuple[int, int]] = set()
    for change_order in change_orders:
        row = _row(change_order)
        file_project = change_order.project_code.strip().upper()
        if not file_project or file_project != page_project:
            raise BusinessException(
                f"{EC_PROJECT_MISMATCH}。工程变更单{row}项目写成{quoted(change_order.project_code)}，"
                f"上传页是{quoted(page_vehicle_model)}。请改成同一个后再传。"
            )
        projects.add(file_project)
        periods.add(parse_effective_period_text(change_order.effective_period_text))
    if len(projects) != 1:
        raise BusinessException(
            f"{EC_PROJECT_MISMATCH}。工程变更单项目写成了 {listed(projects)}。"
            "请改成同一个项目后再传。"
        )
    if len(periods) != 1:
        labels = [format_period(year, month) for year, month in sorted(periods)]
        raise BusinessException(
            f"{EC_EFFECTIVE_MISMATCH}：一次上传只能有一个变更年月。"
            f"工程变更单写成了 {listed(labels)}。"
        )
    year, month = next(iter(periods))
    if year != page_effective_year or month != page_effective_month:
        raise BusinessException(
            f"{EC_EFFECTIVE_MISMATCH}：工程变更单 {format_period(year, month)}，"
            f"上传页 {format_period(page_effective_year, page_effective_month)}"
        )
    return year, month


def _assert_unique_assemblies(change_orders: list[ChangeOrderRowParsed]) -> None:
    """变更前总成、变更后总成各只能出现一次身份；同一总成多场景须连续行并合并单元格。"""
    _assert_unique_assembly_column(
        [
            (
                change_order.before_assembly_part_number.strip(),
                change_order.excel_row,
                change_order.before_assembly_span,
            )
            for change_order in change_orders
            if change_order.before_assembly_part_number.strip()
        ],
        label="变更前总成",
    )
    _assert_unique_assembly_column(
        [
            (
                (change_order.after_assembly_part_number or "").strip(),
                change_order.excel_row,
                change_order.after_assembly_span,
            )
            for change_order in change_orders
            if change_order.change_type != CHANGE_TYPE_STOP
            and (change_order.after_assembly_part_number or "").strip()
        ],
        label="变更后总成",
    )


def _assert_unique_assembly_column(
    items: list[tuple[str, int, tuple[int, int] | None]],
    *,
    label: str,
) -> None:
    groups: dict[str, list[tuple[int, tuple[int, int] | None]]] = {}
    for number, excel_row, span in items:
        groups.setdefault(number, []).append((excel_row, span))
    for number, group in groups.items():
        if len(group) == 1:
            continue
        excel_rows = [row for row, _ in group]
        first = excel_rows[0]
        last = excel_rows[-1]
        contiguous = excel_rows == list(range(first, first + len(excel_rows)))
        expected = (first, last)
        if contiguous and all(span == expected for _, span in group):
            continue
        row_text = f"第 {listed(excel_rows)} 行"
        if contiguous:
            raise BusinessException(
                f"{EC_CHANGE_ORDER_ASSEMBLY_REPEAT}：工程变更单{row_text}的{label}"
                f"都是{quoted(number)}。一个总成改了好几处，请把这几行的「{label}」"
                "格子上下合并成一格。"
            )
        raise BusinessException(
            f"{EC_CHANGE_ORDER_ASSEMBLY_REPEAT}：工程变更单{row_text}都写了{label}"
            f"{quoted(number)}。同一个总成不要隔开写。请改成不同的号，"
            f"或者把这几行挨着写并把「{label}」上下合并成一格。"
        )


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
        missing = expected - file_l0
        extra = file_l0 - expected
        parts: list[str] = []
        if missing:
            parts.append(f"材料清单缺 {listed(missing)}")
        if extra:
            parts.append(f"材料清单多了 {listed(extra)}")
        raise BusinessException(
            f"{EC_BOM_NEW_ROOT}：{'；'.join(parts)}。"
            "完成停止不要写进材料清单；其它改法的变更后总成必须写上。"
        )
    stop_numbers = {
        change_order.before_assembly_part_number.strip()
        for change_order in change_orders
        if change_order.change_type == CHANGE_TYPE_STOP
    }
    overlap = file_l0 & stop_numbers
    if overlap:
        raise BusinessException(
            f"{EC_BOM_NEW_ROOT}：完成停止的总成 {listed(overlap)} 不要写进材料清单。"
        )


def validate_change_order_row(
    change_order: ChangeOrderRowParsed,
    *,
    page_vehicle_model: str,
    page_effective_year: int,
    page_effective_month: int,
) -> tuple[int, int]:
    """单行：先项目信息，再十列填法。"""
    year, month = validate_change_order_project(
        [change_order],
        page_vehicle_model=page_vehicle_model,
        page_effective_year=page_effective_year,
        page_effective_month=page_effective_month,
    )
    validate_change_order_row_shape(change_order)
    return year, month


def validate_change_order_row_shape(change_order: ChangeOrderRowParsed) -> None:
    """变更类型、零件层级、十列填法。"""
    row = _row(change_order)
    if change_order.change_type not in CHANGE_TYPES:
        raise BusinessException(
            f"{EC_CHANGE_ORDER_TYPE_INVALID}：{row}写成{quoted(change_order.change_type)}。"
        )
    if change_order.part_level not in PART_LEVELS:
        raise BusinessException(
            f"{EC_CHANGE_ORDER_COLUMNS}：{row}零件层级写成{quoted(change_order.part_level)}，"
            "只准总成 / 一级 / 二级。"
        )
    if not change_order.before_assembly_part_number:
        raise BusinessException(f"{EC_CHANGE_ORDER_COLUMNS}：{row}变更前总成没有填。")
    _validate_columns_by_type(change_order)


def validate_change_order_before_after(
    change_order: ChangeOrderRowParsed,
    *,
    old_nodes: Sequence[BomNode],
    after_assembly: BomNode | None,
    after_part_as_l0: BomNode | None = None,
) -> None:
    """第二道：变更前必须已有；变更后不得已有（总成；有零件列时同样）。"""
    if change_order.after_assembly_part_number:
        validate_after_assembly_absent(
            after_assembly, part_number=change_order.after_assembly_part_number
        )
    before_part = (change_order.before_part_number or "").strip()
    after_part = (change_order.after_part_number or "").strip()
    expected_level = PART_LEVEL_TO_BOM_LEVEL.get(change_order.part_level)
    if before_part:
        match = next(
            (
                node
                for node in old_nodes
                if (node.part_number or "").strip() == before_part
                and expected_level is not None
                and int(node.level) == expected_level
            ),
            None,
        )
        if match is None:
            raise BusinessException(
                f"{EC_PART_NOT_ON_TREE}：{quoted(before_part)} 不在变更前总成上，"
                f"或不是{quoted(change_order.part_level)}。"
            )
    if not after_part:
        return
    old_numbers = {(node.part_number or "").strip() for node in old_nodes}
    if after_part in old_numbers:
        raise BusinessException(
            f"{EC_ADD_ALREADY_ON_TREE}：{quoted(after_part)} 已在变更前总成上。"
        )
    if after_part_as_l0 is not None:
        raise BusinessException(
            f"{EC_AFTER_ASSEMBLY_EXISTS}：变更后零件 {quoted(after_part)} 系统里已有交货总成。",
            code=409,
        )


def _validate_columns_by_type(change_order: ChangeOrderRowParsed) -> None:
    change_type = change_order.change_type
    row = _row(change_order)
    if change_type == CHANGE_TYPE_STOP:
        if change_order.part_level != PART_LEVEL_ASSEMBLY:
            raise BusinessException(
                f"{EC_CHANGE_ORDER_COLUMNS}：{row}完成停止的零件层级应写「总成」，"
                f"现在是{quoted(change_order.part_level)}。"
            )
        if change_order.after_assembly_part_number:
            raise BusinessException(
                f"{EC_CHANGE_ORDER_COLUMNS}：{row}完成停止不要填变更后总成"
                f"{quoted(change_order.after_assembly_part_number)}。"
            )
        if (
            change_order.before_part_number
            or change_order.after_part_number
            or change_order.part_name
        ):
            raise BusinessException(f"{EC_CHANGE_ORDER_COLUMNS}：{row}完成停止零件那三格请留空。")
        return

    if not change_order.after_assembly_part_number:
        raise BusinessException(f"{EC_CHANGE_ORDER_COLUMNS}：{row}{change_type}必须填变更后总成。")

    if change_type == CHANGE_TYPE_REVISE:
        if change_order.part_level == PART_LEVEL_ASSEMBLY:
            if (
                change_order.before_part_number
                or change_order.after_part_number
                or change_order.part_name
            ):
                raise BusinessException(
                    f"{EC_CHANGE_ORDER_COLUMNS}：{row}改图层级是总成时，零件那三格请留空。"
                )
        else:
            if not change_order.before_part_number or not change_order.after_part_number:
                raise BusinessException(
                    f"{EC_ADD_VS_REVISE}：{row}改图必须填变更前零件和变更后零件。"
                )
        return

    if change_type == CHANGE_TYPE_ADD_PART:
        if change_order.part_level not in {PART_LEVEL_L1, PART_LEVEL_L2}:
            raise BusinessException(
                f"{EC_CHANGE_ORDER_COLUMNS}：{row}增加零件层级只准一级 / 二级，"
                f"现在是{quoted(change_order.part_level)}。"
            )
        if change_order.before_part_number:
            raise BusinessException(
                f"{EC_CHANGE_ORDER_COLUMNS}：{row}增加零件变更前零件应空，"
                f"现在是{quoted(change_order.before_part_number)}。"
            )
        if not change_order.after_part_number:
            raise BusinessException(f"{EC_CHANGE_ORDER_COLUMNS}：{row}增加零件必须填变更后零件。")
        if change_order.after_part_number == change_order.after_assembly_part_number:
            raise BusinessException(
                f"{EC_ADD_VS_REVISE}：{row}增加零件把新零件号"
                f"{quoted(change_order.after_part_number)}写成了变更后总成。"
                "应加在原来的总成上。"
            )
        return

    if change_type == CHANGE_TYPE_NOT_INSTALL:
        if change_order.part_level not in {PART_LEVEL_L1, PART_LEVEL_L2}:
            raise BusinessException(
                f"{EC_CHANGE_ORDER_COLUMNS}：{row}此件不装层级只准一级 / 二级，"
                f"现在是{quoted(change_order.part_level)}。"
            )
        if not change_order.before_part_number:
            raise BusinessException(f"{EC_CHANGE_ORDER_COLUMNS}：{row}此件不装必须填变更前零件。")
        if change_order.after_part_number:
            raise BusinessException(
                f"{EC_CHANGE_ORDER_COLUMNS}：{row}此件不装变更后零件应空，"
                f"现在是{quoted(change_order.after_part_number)}。"
            )
        return

    raise BusinessException(
        f"{EC_CHANGE_ORDER_TYPE_INVALID}：{row}写成{quoted(change_order.change_type)}。"
    )


def validate_before_assembly_active(
    root: BomNode | None,
    *,
    effective_year: int,
    effective_month: int,
    part_number: str = "",
) -> BomNode:
    """
    变更前总成须存在且在切点前一月仍有效；生效月须晚于旧总成生效月。

    切点前一月须有效：工程变更生效月才「切」旧树，前一月旧月账仍要看见 AA。
    切点当月若仍有效也可：导入瞬间旧树尚未被标失效。
    """
    as_of = format_period(effective_year, effective_month)
    if root is None or root.level != 0:
        raise BusinessException(
            f"{EC_BEFORE_ASSEMBLY_INVALID}：系统里没有有效的变更前总成 {quoted(part_number)}。"
            f"请核对该号是否已导入、上传页 {as_of} 是否对。"
        )
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
        raise BusinessException(
            f"{EC_BEFORE_ASSEMBLY_INVALID}：{quoted(part_number)} 在 {as_of} 已失效。"
        )
    if period(effective_year, effective_month) <= period(root.effective_year, root.effective_month):
        raise BusinessException(
            f"{EC_EFFECTIVE_TOO_EARLY}：上传 {as_of}，"
            f"旧总成 {quoted(part_number)} 从 {format_period(root.effective_year, root.effective_month)} 才开始。"
            "生效月必须更晚。"
        )
    return root


def validate_after_assembly_absent(existing: BomNode | None, *, part_number: str = "") -> None:
    if existing is not None:
        raise BusinessException(
            f"{EC_AFTER_ASSEMBLY_EXISTS}：变更后总成 {quoted(part_number or existing.part_number)} 系统里已有。",
            code=409,
        )
