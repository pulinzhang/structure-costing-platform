"""工程变更工艺硬门禁：缺新号、多余新号、旧号仍挂其它有效总成。"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.common.bom.manufacturing_category import resolve_manufacturing_category
from app.common.engineering_change_gates import (
    CHANGE_TYPE_ADD_PART,
    CHANGE_TYPE_REVISE,
    CHANGE_TYPE_STOP,
    EC_PROCESS_EXTRA_NEW,
    EC_PROCESS_MISSING_NEW,
    EC_PROCESS_SHARED_OLD,
    PART_LEVEL_ASSEMBLY,
    after_assembly_not_on_bom_message,
    listed,
    quoted,
)
from app.exceptions.base import BusinessException
from app.parsers.bom.bom_parser import BomParsedNode
from app.parsers.engineering_change.change_order_parser import ChangeOrderRowParsed
from app.parsers.engineering_change.sheet_extract import SHEET_PROCESS
from app.parsers.stamping.models.parse_result import ParserResult
from app.parsers.stamping.stamping_parser import parse_stamping_excel
from app.services.bom.bom.engineering import BomEngineeringService
from app.services.stamping.part.engineering.service import StampingEngineeringService


@dataclass(slots=True)
class ProcessGateItem:
    """一本变更单行对应的工艺门禁输入。"""

    change_order: ChangeOrderRowParsed
    before_root_id: int
    sliced_nodes: list[BomParsedNode] | None


def discover_bom_process_news(
    *,
    change_order: ChangeOrderRowParsed,
    old_tree_numbers: set[str],
    parsed_nodes: list[BomParsedNode],
) -> tuple[dict[str, str], set[str]]:
    """
    材料清单相对旧树的换号 / 新加（供工艺门禁）。
    返回 (旧号→新号, 全新号集合)。不含 L0 总成换号。
    """
    bumps: dict[str, str] = {}
    adds: set[str] = set()
    if change_order.change_type == CHANGE_TYPE_REVISE:
        if (
            change_order.part_level != PART_LEVEL_ASSEMBLY
            and change_order.before_part_number
            and change_order.after_part_number
        ):
            bumps[change_order.before_part_number.strip()] = change_order.after_part_number.strip()
    elif change_order.change_type == CHANGE_TYPE_ADD_PART and change_order.after_part_number:
        adds.add(change_order.after_part_number.strip())

    file_numbers = {
        (node.part_number or "").strip()
        for node in parsed_nodes
        if node.level > 0 and (node.part_number or "").strip()
    }
    old_numbers = {(number or "").strip() for number in old_tree_numbers if number}
    mapped_news = set(bumps.values())
    for file_number in file_numbers:
        if file_number in old_numbers or file_number in mapped_news or file_number in adds:
            continue
        adds.add(file_number)
    return bumps, adds


def validate_process_hard_gates(
    db: Session,
    *,
    items: list[ProcessGateItem],
    location: str,
    vehicle_model: str,
    effective_year: int,
    effective_month: int,
    process_part_numbers: set[str],
    bom_service: BomEngineeringService | None = None,
    stamping_service: StampingEngineeringService | None = None,
) -> dict[str, str]:
    """
    整本工艺硬门禁。完成停止 / 此件不装：该行不必出工艺。
    返回改图钉明的旧号→新号（工艺/布点只停变更单写出的旧号，不按茎猜）。
    """
    bom = bom_service or BomEngineeringService()
    stamping = stamping_service or StampingEngineeringService()
    process_numbers = process_part_numbers
    as_of_rows = stamping.list_parts_as_of_for_engineering_change(
        db,
        location=location,
        vehicle_model=vehicle_model,
        as_of_year=effective_year,
        as_of_month=effective_month,
    )
    as_of_numbers = {(row.part_number or "").strip() for row in as_of_rows}
    exclude_l0_ids = {item.before_root_id for item in items}

    allowed_new: set[str] = set()
    revise_old_to_new: dict[str, str] = {}
    for item in items:
        if item.change_order.change_type == CHANGE_TYPE_STOP:
            continue
        nodes = item.sliced_nodes
        if nodes is None:
            raise BusinessException(
                after_assembly_not_on_bom_message(item.change_order.after_assembly_part_number)
            )
        old_nodes = bom.list_subtree_nodes(db, root_id=item.before_root_id)
        old_tree_numbers = {(node.part_number or "").strip() for node in old_nodes}
        bumps, adds = discover_bom_process_news(
            change_order=item.change_order,
            old_tree_numbers=old_tree_numbers,
            parsed_nodes=nodes,
        )
        allowed_new |= set(bumps.values()) | adds
        if item.change_order.change_type == CHANGE_TYPE_REVISE:
            revise_old_to_new.update(bumps)
            for old_number, new_number in bumps.items():
                if old_number not in as_of_numbers:
                    continue
                if new_number not in process_numbers:
                    raise BusinessException(
                        f"{EC_PROCESS_MISSING_NEW}：{quoted(new_number)}。"
                        "请在冲压工艺确认表写出这一号。"
                    )
                if bom.part_number_used_on_other_active_l0(
                    db,
                    location=location,
                    vehicle_model=vehicle_model,
                    part_number=old_number,
                    as_of_year=effective_year,
                    as_of_month=effective_month,
                    exclude_l0_ids=exclude_l0_ids,
                ):
                    raise BusinessException(
                        f"{EC_PROCESS_SHARED_OLD}：{quoted(old_number)} "
                        "还装在别的交货总成上，这一行不能按改图停掉。"
                    )
        if (
            item.change_order.change_type == CHANGE_TYPE_ADD_PART
            and item.change_order.after_part_number
        ):
            required = item.change_order.after_part_number.strip()
            add_row = next(
                (node for node in reversed(nodes) if (node.part_number or "").strip() == required),
                None,
            )
            if (
                required
                and add_row is not None
                and _parsed_needs_process(nodes, add_row)
                and required not in process_numbers
            ):
                raise BusinessException(
                    f"{EC_PROCESS_MISSING_NEW}：{quoted(required)}。"
                    "请在冲压工艺确认表写出这一号。"
                )

    process_new = {number for number in process_numbers if number not in as_of_numbers}
    extra = process_new - allowed_new
    if extra:
        raise BusinessException(
            f"{EC_PROCESS_EXTRA_NEW}：{listed(extra)}。"
            "冲压工艺确认表只写这次换号或新加的冲压件。请删掉多出来的号，或把这些号写进材料清单后再传。"
        )
    return revise_old_to_new


def _parsed_needs_process(nodes: list[BomParsedNode], add_row: BomParsedNode) -> bool:
    """增加零件：只有自制冲压件才必须出工艺号。胶、标准件、分总成不要。"""
    parent_index = next(
        (index for index, node in enumerate(nodes) if node is add_row),
        None,
    )
    if parent_index is not None and any(node.parent_index == parent_index for node in nodes):
        return False
    role = (add_row.node_role or "").strip().lower()
    if role in {"consumable", "buy", "structure"}:
        return False
    if (add_row.qty_unit or "").strip().lower() == "mm":
        return False
    blob = " ".join(
        part
        for part in (
            add_row.part_name,
            add_row.material,
            add_row.thickness_text,
        )
        if part
    )
    if any(key in blob for key in ("胶", "发泡", "环氧", "TEROSON", "teroson")):
        return False
    # Parser 缺料厚时常把叶子标成 make，不能据此当成冲压件。
    category = resolve_manufacturing_category(
        node_role=None if role == "make" else add_row.node_role,
        is_supply_unit=False,
        has_children=False,
        part_name=add_row.part_name,
        material=add_row.material,
        part_number=add_row.part_number,
        thickness_mm=add_row.thickness_mm,
        qty_unit=add_row.qty_unit,
    )
    return category == "stamping"


def parse_process_confirmation(file_content: bytes | None) -> ParserResult:
    """整本或抽出的 xlsx → 「冲压工艺确认表」。空字节当空表。"""
    if not file_content:
        return ParserResult()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name
    try:
        return parse_stamping_excel(tmp_path, sheet_title=SHEET_PROCESS)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
